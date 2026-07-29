"""Auth command — save HF token to DB with validation."""
# pyright: reportCallInDefaultInitializer=false
from __future__ import annotations

import asyncio

import typer
from huggingface_hub import HfApi

from hf_sync.cli.app import app, console
from hf_sync.config import settings
from hf_sync.database import Database


@app.command()
def auth(
    token: str = typer.Argument(
        help="Hugging Face token (hf_...)",
    ),
) -> None:
    """Save HF token to DB with validation."""
    if not token.startswith("hf_"):
        console.print("[yellow]Token should start with hf_[/yellow]")

    # Validate token against Hugging Face API
    try:
        HfApi(token=token).whoami()
    except Exception as e:
        console.print(f"[red]✗ Token validation failed: {e}[/red]")
        raise typer.Exit(1) from e

    async def _save() -> None:
        db = Database(settings.db_path)
        await db.set_config("hf_token", token)

    asyncio.run(_save())

    # Update current session token
    settings.hf_token = token

    console.print("[green]✓ Token validated and saved[/green]")
