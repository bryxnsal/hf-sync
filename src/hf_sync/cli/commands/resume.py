"""Resume command — retry failed files."""
# pyright: reportCallInDefaultInitializer=false
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

from hf_sync.cli.app import app, console
from hf_sync.config import settings
from hf_sync.database import Database
from hf_sync.logger import setup_logger


@app.command()
def resume() -> None:
    """Retry failed files (reset FAILED → PENDING)."""
    setup_logger(settings.log_level)
    asyncio.run(_resume_impl())


async def _resume_impl() -> None:
    conn = await Database(settings.db_path).connect()
    # Reset failed + interrupted states so they get picked up by next start
    cur = await conn.execute(
        "SELECT id, local_path FROM files WHERE status IN ('FAILED', 'DOWNLOADING', 'UPLOADING', 'VERIFYING')"
    )
    rows = await cur.fetchall()
    file_list = list(rows)
    for row in file_list:
        # Clean up any leftover temp file from interrupted/failed run
        p = Path(cast(str, row["local_path"]))
        if p.is_file():
            p.unlink()
    _ = await conn.execute(
        "UPDATE files SET status = 'PENDING', updated_at = datetime('now')"
        + " WHERE status IN ('FAILED', 'DOWNLOADING', 'UPLOADING', 'VERIFYING')"
    )
    await conn.commit()
    await conn.close()
    console.print(f"[green]Reset {len(file_list)} files to PENDING — run 'hf-sync start' to retry[/green]")
