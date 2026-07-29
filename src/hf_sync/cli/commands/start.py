"""Start command — run the sync pipeline."""
# pyright: reportCallInDefaultInitializer=false
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, cast

import typer
from loguru import logger
from rich.console import Group
from rich.live import Live
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from rich.progress import TaskID
from rich.table import Table

from hf_sync.cli.app import app, console
from hf_sync.cli.shared.display import _fmt_elapsed, _FrozenBar, _parse_destination, _show_dry_run
from hf_sync.config import settings
from rich.text import Text
from hf_sync.database import Database
from hf_sync.engine.cleanup import Cleanup
from hf_sync.engine.coordinator import Coordinator
from hf_sync.engine.downloader import Downloader
from hf_sync.engine.uploader import Uploader
from hf_sync.engine.verifier import Verifier
from hf_sync.logger import setup_logger
from hf_sync.repositories.files import FileRepository
from hf_sync.services.aria2 import Aria2Service
from hf_sync.services.huggingface import HuggingFaceService
from hf_sync.services.rclone import RcloneService
from hf_sync.types.dto import SyncTask
from hf_sync.utils.bytes import human_size


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
    # Suppress console logging first — redirect all to file
    logger.remove()
    _ = logger.add("hf-sync.log", level="DEBUG", rotation="10 MB")

    Path(settings.temp_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = await Database(settings.db_path).connect()
    repo = FileRepository(conn)

    # Auto-init if DB is empty: scan repo and populate pending files
    cur = await conn.execute("SELECT COUNT(*) as cnt FROM files")
    row = await cur.fetchone()
    file_count: int = cast(int, row["cnt"]) if row else 0
    if file_count == 0:
        console.print(f"[dim]Scanning repo {repo_id}...[/dim]")
        hf = HuggingFaceService(settings.hf_token)
        files = hf.list_files(repo_id)
        for f in files:
            fn: str = cast(str, f["filename"])
            existing = await repo.get_by_name(fn)
            if existing is None:
                _ = await repo.insert(
                    filename=fn,
                    size=int(cast(int, f.get("size", 0))),  # type: ignore[arg-type]
                    status="PENDING",
                    local_path=str(Path(settings.temp_dir) / fn),
                )
        console.print(f"[dim]Found {len(files)} files[/dim]")

    # Count total pending
    cur = await conn.execute("SELECT COUNT(*) as cnt FROM files WHERE status = 'PENDING'")
    row = await cur.fetchone()
    total: int = cast(int, row["cnt"]) if row else 0
    if total == 0:
        console.print("[yellow]No files to sync[/yellow]")
        await conn.close()
        return

    aria2 = Aria2Service(settings.aria2_rpc_url, settings.aria2_rpc_secret)
    rclone = RcloneService(rclone_remote)
    coordinator = Coordinator(
        Downloader(aria2), Uploader(rclone), Verifier(), Cleanup(),
        repo, settings.temp_dir,
    )
    hf = HuggingFaceService(settings.hf_token)

    _sep = Text("")

    # File progress bar — re-created per file
    file_progress = Progress(
        TextColumn("{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TextColumn("{task.fields[speed]}"),
        console=console,
    )
    file_task = file_progress.add_task("[dim]Waiting...[/dim]", total=100, speed="")

    done = 0
    failed = 0
    completed_lines: list[_FrozenBar] = []

    def build_display() -> Group:
        items: list[Any] = list(completed_lines)
        if items:
            items.append(_sep)
        items.append(file_progress)
        return Group(*items)

    with Live(build_display(), console=console, refresh_per_second=4) as live:
        while True:
            row = await repo.get_pending()
            if row is None:
                break

            file_id: int = cast(int, row["id"])
            filename: str = cast(str, row["filename"])
            src_url = hf.get_signed_url(repo_id, filename)
            remote_file = f"{rclone_remote}:{rclone_path}/{filename}" if rclone_path else f"{rclone_remote}:{filename}"
            size: int = cast(int, row["size"])
            idx = done + failed + 1

            # Fresh task per file so elapsed timer resets
            file_progress.remove_task(file_task)
            file_task = file_progress.add_task(
                f"[green][{idx}/{total}] {filename} ({human_size(size)})",
                total=100, speed="",
            )

            task = SyncTask(
                file_id=file_id,
                filename=filename,
                source_url=src_url,
                local_path=cast(str, row["local_path"]),
                remote_path=remote_file,
                size=size,
                sha256=cast(str, row["sha256"]),
            )

            # Progress callback updates the file bar live during download
            def on_progress(
                stage: str, pct: float, speed: str,
                _fn: str = filename, _sz: int = size, _idx: int = idx,
                _task: TaskID = file_task,
            ) -> None:
                color = {"download": "green", "upload": "blue", "verify": "yellow"}.get(stage, "green")
                icon = {"download": "⬇ ", "upload": "⬆ ", "verify": "🔍 "}.get(stage, "")
                speed_str = f"  @ {speed}" if speed else ""
                file_progress.update(
                    _task,
                    description=f"[{color}][{_idx}/{total}] {icon}{_fn} ({human_size(_sz)}){speed_str}",
                    completed=pct,
                    speed="",
                )

            start = time.time()
            ok, err = await coordinator.run(task, progress_callback=on_progress)
            elapsed = _fmt_elapsed(time.time() - start)
            sz_str = human_size(size)

            if ok:
                done += 1
                completed_lines.append(_FrozenBar(idx, total, filename, sz_str, elapsed, "OK", True))
            else:
                failed += 1
                completed_lines.append(_FrozenBar(idx, total, filename, sz_str, elapsed, err, False))

            # Keep last 10 completed visible
            if len(completed_lines) > 10:
                _ = completed_lines.pop(0)

            live.update(build_display())

        # Final: mark pipeline complete
        file_progress.remove_task(file_task)
        _ = file_progress.add_task("[green]✓ Pipeline complete", total=100, completed=100, speed="")

    # Restore loguru
    from hf_sync.logger import setup_logger
    setup_logger(settings.log_level)

    # Summary
    await conn.commit()
    cur = await conn.execute("SELECT status, COUNT(*) as cnt FROM files GROUP BY status")
    rows = await cur.fetchall()
    await conn.close()

    summary_table = Table(title="Results", show_header=False)
    summary_table.add_column("Status", style="bold")
    summary_table.add_column("Count")
    summary_table.add_row("[green]DONE[/green]", str(done))
    summary_table.add_row("[red]FAILED[/red]", str(failed))
    summary_table.add_row("[dim]Total[/dim]", str(done + failed))
    for row in rows:
        s = str(row["status"])
        c = str(row["cnt"])
        if s in ("DONE", "FAILED"):
            continue  # already shown
        summary_table.add_row(f"[yellow]{s}[/yellow]", c)

    console.print()
    console.print(summary_table)
