"""Shared display utilities for CLI."""
from __future__ import annotations

from rich.console import Console, ConsoleOptions
from rich.table import Table
from rich.text import Text

from hf_sync.cli.app import console
from hf_sync.services.doctor import DoctorService



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


class _FrozenBar:
    """Frozen progress bar line for a completed file."""

    def __init__(self, idx: int, total: int, filename: str, size_str: str,
                 elapsed: str, status: str, is_ok: bool) -> None:
        self.idx: int = idx
        self.total: int = total
        self.filename: str = filename
        self.size_str: str = size_str
        self.elapsed: str = elapsed
        self.status: str = status
        self.is_ok: bool = is_ok

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> Text:
        from rich.text import Text
        max_width: int = options.max_width or 0
        icon = "\u2713" if self.is_ok else "\u2717"
        prefix = f"[{self.idx}/{self.total}] {icon} {self.filename} ({self.size_str})"
        if self.is_ok:
            suffix = f" 100% {self.elapsed} {self.status}"
        else:
            suffix = f" {self.elapsed} {self.status}"
        bar_width = max(max_width - len(prefix) - len(suffix) - 2, 10)
        bar = "\u2501" * bar_width
        style = "green" if self.is_ok else "red"
        text = Text(prefix)
        _ = text.append(" ")
        _ = text.append(bar, style=style)
        _ = text.append(suffix, style=style)
        return text


def _fmt_elapsed(seconds: float) -> str:
    """Format seconds as MM:SS or HH:MM:SS."""
    seconds = int(seconds)
    h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
