"""Config command — interactively configure settings in DB."""
# pyright: reportCallInDefaultInitializer=false
from __future__ import annotations

import asyncio

from hf_sync.cli.app import app, console
from hf_sync.config import settings
from hf_sync.database import Database


@app.command()
def config() -> None:
    """Interactively configure settings (stored in DB)."""
    db = Database(settings.db_path)

    async def _interactive() -> None:
        # Build list of (field, label, current_value, default_value)
        fields = [
            ("hf_repo_id", "HF_REPO_ID", settings.hf_repo_id, ""),
            ("aria2_rpc_url", "ARIA2_RPC_URL", settings.aria2_rpc_url, "http://localhost:6800/jsonrpc"),
            ("aria2_rpc_secret", "ARIA2_RPC_SECRET", settings.aria2_rpc_secret, ""),
            ("rclone_remote", "RCLONE_REMOTE", settings.rclone_remote, ""),
            ("rclone_path", "RCLONE_PATH", settings.rclone_path, ""),
        ]

        console.print("[bold]HF Sync Configuration[/bold]\n")
        console.print("Press Enter to keep current value (shown in brackets).\n")

        for field, label, current, default in fields:
            display = current or default or "(not set)"
            new_val = input(f"  {label} [{display}]: ").strip()
            if new_val:
                await db.set_config(field, new_val)
                setattr(settings, field, new_val)

        console.print()
        console.print("[green]✓ Configuration saved to DB[/green]")

    asyncio.run(_interactive())
