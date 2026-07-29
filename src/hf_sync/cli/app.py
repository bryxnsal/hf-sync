"""App instance and console."""
# pyright: reportCallInDefaultInitializer=false
from __future__ import annotations

import typer
from rich.console import Console

console = Console()


def _version_callback(value: bool) -> None:
    if value:
        try:
            from hf_sync._version import __version__ as ver
        except Exception:
            ver = "0.0.0"
        console.print(f"hf-sync v{ver}")
        raise typer.Exit()


app = typer.Typer(
    add_completion=False,
    context_settings={"help_option_names": ["--help", "-h"]},
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit",
        is_eager=True,
        callback=_version_callback,
    ),
) -> None:
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()
