"""App instance and console."""
from __future__ import annotations

import typer
from rich.console import Console

console = Console()
app = typer.Typer()
