"""Table rendering utilities using Rich."""

from __future__ import annotations

from rich.table import Table
from rich.console import Console


def render_table(title: str, headers: list[str], rows: list[list[str]]) -> str:
    """Render a Rich table and return as string."""
    table = Table(title=title)
    for h in headers:
        table.add_column(h)
    for row in rows:
        table.add_row(*row)
    console = Console()
    with console.capture() as capture:
        console.print(table)
    return capture.get()
