"""CLI entry point using Typer.

Commands:
  hf-sync auth <token>       — save HF token to config file
  hf-sync doctor             — check system health
  hf-sync init [repo_id]     — create DB, index repo files
  hf-sync start [repo_id] [dest]  — run sync pipeline (--dry-run for pre-flight)
  hf-sync resume             — retry failed files
  hf-sync verify             — verify downloaded files
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from hf_sync.config import settings
from hf_sync.database import Database
from hf_sync.engine.cleanup import Cleanup
from hf_sync.engine.coordinator import Coordinator
from hf_sync.engine.downloader import Downloader
from hf_sync.engine.uploader import Uploader
from hf_sync.engine.verifier import Verifier
from hf_sync.logger import setup_logger
from hf_sync.repositories.files import FileRepository
from hf_sync.services.aria2 import Aria2Service
from hf_sync.services.doctor import DoctorService
from hf_sync.services.huggingface import HuggingFaceService
from hf_sync.services.rclone import RcloneService
from hf_sync.types.dto import SyncTask
from hf_sync.utils.bytes import human_size

# Ruta del archivo de configuración (misma lógica que en config.py)
_CONFIG_PATH = Path(os.environ.get(
    "HF_SYNC_CONFIG",
    str(Path.home() / ".config" / "hf-sync" / ".env"),
))

console = Console()
app = typer.Typer()


def _parse_destination(dest: str) -> tuple[str, str]:
    """Split 'remote:path' into (remote, path)."""
    if ":" in dest:
        parts = dest.split(":", 1)
        return parts[0], parts[1]
    return dest, ""


def _show_dry_run(repo_id: str, destination: str) -> None:
    """Show pre-flight checks without running the pipeline."""
    report = DoctorService.dry_run(repo_id, destination)

    def tag(ok: bool) -> str:
        return "[green]✓[/green]" if ok else "[red]✗[/red]"

    def fmt(b: int) -> str:
        return f"{b/(1024**3):.1f}G" if b > 1024**3 else f"{b/(1024**2):.1f}M"

    table = Table(title="HF Sync — Dry Run")
    table.add_column("Check", style="bold")
    table.add_column("Result")

    table.add_row(f"Repo: {repo_id}", tag(report.repo_accessible))
    if report.repo_accessible:
        table.add_row("  Files", str(report.file_count))
        table.add_row("  Total", fmt(report.total_size))
        if report.largest_file_name:
            table.add_row("  Largest", f"{report.largest_file_name} ({fmt(report.largest_file_size)})")

    table.add_row(f"Local disk ({report.local_free_gb}G free)", tag(report.local_ok))

    dest_label = destination
    table.add_row(f"Destination: {dest_label}", tag(report.dest_accessible))
    if report.remote_free_gb > 0:
        table.add_row(f"  Remote space ({report.remote_free_gb}G free)", tag(report.remote_ok))

    console.print(table)

    if not report.local_ok:
        console.print("[red]✗ Not enough local disk space[/red]")
    if not report.remote_ok:
        console.print("[red]✗ Not enough space at destination[/red]")


# ── auth ────────────────────────────────────────────────────────────────


@app.command()
def auth(
    token: str = typer.Argument(
        help="Hugging Face token (hf_...)",
    ),
) -> None:
    """Save HF token to config file."""
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not token.startswith("hf_"):
        console.print("[yellow]Token should start with hf_[/yellow]")

    # Read existing .env or start fresh
    lines: list[str] = []
    if _CONFIG_PATH.exists():
        lines = _CONFIG_PATH.read_text().splitlines()

    # Reemplazar o agregar HF_TOKEN
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith("HF_TOKEN="):
            lines[i] = f"HF_TOKEN={token}"
            found = True
            break
    if not found:
        lines.append(f"HF_TOKEN={token}")

    _CONFIG_PATH.write_text("\n".join(lines) + "\n")
    console.print(f"[green]✓ Token saved to {_CONFIG_PATH}[/green]")


# ── doctor ──────────────────────────────────────────────────────────────


@app.command()
def doctor(
    repo_id: str = typer.Argument(
        default=None,
        help="HF repo ID (optional, checks largest file disk space)",
    ),
    destination: str = typer.Argument(
        default=None,
        help="rclone destination (e.g. googledrive:models/llama)",
    ),
) -> None:
    """Check system health. Optionally validate repo + destination space."""
    if repo_id and destination:
        # Full dry-run mode
        _show_dry_run(repo_id, destination)
        return

    svc = DoctorService()
    report = svc.check_all()

    def tag(ok: bool, configured: bool = True) -> str:
        if not configured:
            return "[dim]—[/dim]"
        return "[green]✓[/green]" if ok else "[red]✗[/red]"

    def hint(msg: str) -> str:
        return f" [dim]({msg})[/dim]" if msg else ""

    table = Table(title="HF Sync — Doctor")
    table.add_column("Check", style="bold")
    table.add_column("Status")

    aria2_status = tag(report.aria2)
    if report.aria2_error:
        aria2_status += hint(report.aria2_error)
    table.add_row("aria2 RPC", aria2_status)

    table.add_row("rclone binary", tag(report.rclone))
    table.add_row("HF token", tag(report.hf_token, report.hf_token_configured))

    drive_status = tag(report.drive_access, report.drive_configured)
    if report.drive_error:
        drive_status += hint(report.drive_error)
    table.add_row("Drive access", drive_status)

    free_tag = tag(report.free_space_gb > 1, report.drive_configured)
    table.add_row(f"Free space ({report.free_space_gb} GB)", free_tag)
    table.add_row("Permissions", tag(report.permissions_ok))

    console.print(table)

    # Hints for common issues
    if not report.aria2:
        console.print("  [yellow]→ Run: aria2c --enable-rpc --rpc-listen-all[/yellow]")
    if not report.hf_token and not report.hf_token_configured:
        console.print("  [yellow]→ Run: hf-sync auth <your_token>[/yellow]")
    if not report.drive_access and report.drive_configured:
        console.print("  [yellow]→ Check rclone config: rclone config[/yellow]")
    if not report.drive_configured:
        console.print("  [yellow]→ Set RCLONE_REMOTE in .env or configure rclone remotes[/yellow]")


# ── init ────────────────────────────────────────────────────────────────


@app.command()
def init(
    repo_id: str = typer.Argument(
        default=None,
        help="HF repo ID (e.g. databricks/dolly-v2-3b). Optional if set in .env",
    ),
) -> None:
    """Initialize DB and scan repo files."""
    setup_logger(settings.log_level)
    asyncio.run(_init_impl(repo_id or settings.hf_repo_id))


async def _init_impl(repo_id: str) -> None:
    Path(settings.temp_dir).mkdir(parents=True, exist_ok=True)

    await Database.init_db(settings.db_path)
    logger.info("DB ready at {}", settings.db_path)

    if not settings.hf_token:
        console.print("[yellow]HF_TOKEN not set — skipping repo scan[/yellow]")
        return
    if not repo_id:
        console.print("[yellow]Specify a repo_id or set it in .env[/yellow]")
        return

    hf = HuggingFaceService(settings.hf_token)
    files = hf.list_files(repo_id)
    logger.info("Found {} files in {}", len(files), repo_id)

    conn = await Database(settings.db_path).connect()
    repo = FileRepository(conn)
    for f in files:
        existing = await repo.get_by_name(str(f["filename"]))
        if existing is None:
            await repo.insert(
                filename=str(f["filename"]),
                size=int(f.get("size", 0)),  # type: ignore[arg-type]
                status="PENDING",
                local_path=str(Path(settings.temp_dir) / str(f["filename"])),
            )
    await conn.close()
    console.print(f"[green]Scanned {len(files)} files — ready[/green]")


# ── start ───────────────────────────────────────────────────────────────


@app.command()
def start(
    repo_id: str = typer.Argument(
        default=None,
        help="HF repo ID (e.g. databricks/dolly-v2-3b). Optional if set in .env",
    ),
    destination: str = typer.Argument(
        default=None,
        help="rclone destination (e.g. googledrive:models/llama). Optional if set in .env"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Pre-flight: check repo, local and remote space without syncing",
    ),
) -> None:
    """Run the sync pipeline."""
    setup_logger(settings.log_level)

    repo_id = repo_id or settings.hf_repo_id
    dest = destination or f"{settings.rclone_remote}:{settings.rclone_path}"

    if not settings.hf_token:
        console.print("[red]HF_TOKEN not configured[/red]")
        raise typer.Exit(1)
    if not repo_id:
        console.print("[red]Specify a repo_id or set it in .env[/red]")
        raise typer.Exit(1)
    if not dest or dest == ":":
        console.print("[red]Specify a destination or set RCLONE_REMOTE in .env[/red]")
        raise typer.Exit(1)

    if dry_run:
        _show_dry_run(repo_id, dest)
        return

    rclone_remote, rclone_path = _parse_destination(dest)
    try:
        asyncio.run(_start_impl(repo_id, rclone_remote, rclone_path))
    except KeyboardInterrupt:
        console.print("\n[yellow]Sync cancelled by user[/yellow]")


async def _start_impl(repo_id: str, rclone_remote: str, rclone_path: str) -> None:
    Path(settings.temp_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = await Database(settings.db_path).connect()
    repo = FileRepository(conn)

    # Auto-init if DB is empty: scan repo and populate pending files
    cur = await conn.execute("SELECT COUNT(*) as cnt FROM files")
    row = await cur.fetchone()
    file_count = int(row["cnt"]) if row else 0
    if file_count == 0:
        logger.info("No files in DB — scanning repo {}", repo_id)
        hf = HuggingFaceService(settings.hf_token)
        files = hf.list_files(repo_id)
        for f in files:
            await repo.insert(
                filename=str(f["filename"]),
                size=int(f.get("size", 0)),  # type: ignore[arg-type]
                status="PENDING",
                local_path=str(Path(settings.temp_dir) / str(f["filename"])),
            )
        logger.info("Found {} files — starting sync", len(files))

    # Count total pending
    cur = await conn.execute("SELECT COUNT(*) as cnt FROM files WHERE status = 'PENDING'")
    row = await cur.fetchone()
    total = int(row["cnt"]) if row else 0
    if total == 0:
        console.print("[yellow]No files to sync[/yellow]")
        await conn.close()
        return

    aria2 = Aria2Service(settings.aria2_rpc_url, settings.aria2_rpc_secret)
    rclone = RcloneService(rclone_remote)
    downloader = Downloader(aria2)
    uploader = Uploader(rclone)
    verifier = Verifier()
    cleanup = Cleanup()
    coordinator = Coordinator(downloader, uploader, verifier, cleanup, repo, settings.temp_dir)
    hf = HuggingFaceService(settings.hf_token)

    from rich.progress import Progress, BarColumn, TextColumn, TaskProgressColumn, SpinnerColumn, TimeElapsedColumn

    succeeded = 0
    failed = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        overall = progress.add_task("[cyan]Syncing...", total=total)

        while True:
            row = await repo.get_pending()
            if row is None:
                break

            done = int(progress.tasks[overall].completed)
            file_id = int(row["id"])  # type: ignore[arg-type]
            filename = str(row["filename"])
            src_url = hf.get_signed_url(repo_id, filename)
            remote_file = f"{rclone_remote}:{rclone_path}/{filename}" if rclone_path else f"{rclone_remote}:{filename}"

            size = int(row["size"])  # type: ignore[arg-type]
            progress.update(overall, description=f"[cyan][{done}/{total}] {filename} ({human_size(size)})")

            task = SyncTask(
                file_id=file_id,
                filename=filename,
                source_url=src_url,
                local_path=str(row["local_path"]),
                remote_path=remote_file,
                size=size,
                sha256=str(row["sha256"]),
            )
            ok = await coordinator.run(task)
            if ok:
                succeeded += 1
            else:
                failed += 1
            progress.update(overall, advance=1)

        progress.update(overall, description="[green]✓ Pipeline complete")

    # Summary
    await conn.commit()
    cur = await conn.execute("SELECT status, COUNT(*) as cnt FROM files GROUP BY status")
    rows = await cur.fetchall()
    await conn.close()

    summary_table = Table(title="Results", show_header=False)
    summary_table.add_column("Status", style="bold")
    summary_table.add_column("Count")
    summary_table.add_row("[green]DONE[/green]", str(succeeded))
    summary_table.add_row("[red]FAILED[/red]", str(failed))
    total_processed = succeeded + failed
    summary_table.add_row("[dim]Total[/dim]", str(total_processed))

    for row in rows:
        s = str(row["status"])
        c = str(row["cnt"])
        if s == "DONE":
            continue  # already shown
        if s == "FAILED":
            continue  # already shown
        summary_table.add_row(f"[yellow]{s}[/yellow]", c)

    console.print()
    console.print(summary_table)


# ── resume ──────────────────────────────────────────────────────────────


@app.command()
def resume() -> None:
    """Retry failed files (reset FAILED → PENDING)."""
    setup_logger(settings.log_level)
    asyncio.run(_resume_impl())


async def _resume_impl() -> None:
    conn = await Database(settings.db_path).connect()
    await conn.execute("UPDATE files SET status = 'PENDING', updated_at = datetime('now') WHERE status = 'FAILED'")
    await conn.commit()
    await conn.close()
    console.print("[green]Failed files reset to PENDING — run 'hf-sync start' to retry[/green]")


# ── verify ──────────────────────────────────────────────────────────────


@app.command()
def verify() -> None:
    """Verify integrity of downloaded files."""
    setup_logger(settings.log_level)
    asyncio.run(_verify_impl())


async def _verify_impl() -> None:
    conn = await Database(settings.db_path).connect()
    cur = await conn.execute("SELECT id, filename, local_path, size, sha256, status FROM files WHERE status = 'DONE'")
    rows = await cur.fetchall()
    verifier = Verifier()
    ok_count = 0
    fail_count = 0
    table = Table(title="Verification Results")
    table.add_column("File")
    table.add_column("Result")

    for row in rows:
        ok = verifier.verify(str(row["local_path"]), int(row["size"]), str(row["sha256"]))
        tag = "[green]✓[/green]" if ok else "[red]✗[/red]"
        table.add_row(str(row["filename"]), tag)
        if ok:
            ok_count += 1
        else:
            fail_count += 1

    console.print(table)
    console.print(f"Verified: {ok_count} OK, {fail_count} failed")
    await conn.close()


# ── entry ───────────────────────────────────────────────────────────────


def main() -> None:
    """Typer entry point."""
    app()
