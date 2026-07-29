"""Doctor command — check system health."""
# pyright: reportCallInDefaultInitializer=false
from __future__ import annotations

import typer
from rich.table import Table

from hf_sync.cli.app import app, console
from hf_sync.cli.shared.display import _show_dry_run
from hf_sync.services.doctor import DoctorService


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
