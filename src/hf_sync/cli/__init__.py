"""CLI entry point using Typer.

Commands:
  hf-sync auth <token>       — save HF token to DB (with validation)
  hf-sync config             — interactively configure settings in DB
  hf-sync doctor             — check system health
  hf-sync init [repo_id]     — create DB, index repo files
  hf-sync start [repo_id] [dest]  — run sync pipeline (--dry-run for pre-flight)
  hf-sync resume             — retry failed files
  hf-sync verify             — verify downloaded files
"""

from __future__ import annotations

__all__ = [
    "app",
    "console",
    "_FrozenBar",
    "_fmt_elapsed",
    "_parse_destination",
    "_show_dry_run",
    "main",
]

# Import app first so commands can reference it
from hf_sync.cli.app import app, console  # noqa: F401

# Import command modules to register them with the app
from hf_sync.cli import commands  # noqa: F401  # pyright: ignore[reportUnusedImport]

# Re-export shared utilities for tests and backward compat
from hf_sync.cli.shared.display import (  # noqa: F401
    _FrozenBar,
    _fmt_elapsed,
    _parse_destination,
    _show_dry_run,
)



def main() -> None:
    """Typer entry point."""
    app()
