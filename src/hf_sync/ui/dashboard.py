"""Live dashboard using Rich."""

from __future__ import annotations

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table


class Dashboard:
    """Render a live TUI of the sync pipeline."""

    def __init__(self) -> None:
        self.console = Console()
        self.layout = Layout()
        self._live: Live | None = None

    def start(self) -> None:
        """Enter live rendering mode."""
        self._live = Live(self._build_layout(), console=self.console, refresh_per_second=4)
        self._live.__enter__()  # type: ignore[no-untyped-call]

    def stop(self) -> None:
        """Exit live rendering mode."""
        if self._live:
            self._live.__exit__(None, None, None)  # type: ignore[no-untyped-call]
            self._live = None

    def _build_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(Panel("HF Sync", style="bold cyan"), size=3),
            Layout(Panel("Pipeline idle")),
        )
        return layout

    def update(self, stage: str, filename: str, current: int, total: int) -> None:
        """Refresh the dashboard with current state."""
        if not self._live:
            return
        table = Table(title=f"Pipeline: {stage}")
        table.add_column("File")
        table.add_column("Progress")
        table.add_row(filename, f"{current}/{total}")
        self._live.update(Panel(table))
