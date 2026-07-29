"""Verify command — check integrity of downloaded files."""
# pyright: reportCallInDefaultInitializer=false
from __future__ import annotations

import asyncio
from typing import cast

from rich.table import Table

from hf_sync.cli.app import app, console
from hf_sync.config import settings
from hf_sync.database import Database
from hf_sync.engine.verifier import Verifier
from hf_sync.logger import setup_logger


@app.command()
def verify() -> None:
    """Verify integrity of downloaded files."""
    setup_logger(settings.log_level)
    asyncio.run(_verify_impl())


async def _verify_impl() -> None:
    conn = await Database(settings.db_path).connect()
    cur = await conn.execute("SELECT id, filename, local_path, size, sha256, status FROM files WHERE status = 'DONE'")
    rows = await cur.fetchall()
    verifier = Verifier()
    ok_count = 0
    fail_count = 0
    table = Table(title="Verification Results")
    table.add_column("File")
    table.add_column("Result")

    for row in rows:
        ok = verifier.verify(
            cast(str, row["local_path"]),
            cast(int, row["size"]),
            cast(str, row["sha256"]),
        )
        tag = "[green]✓[/green]" if ok else "[red]✗[/red]"
        table.add_row(cast(str, row["filename"]), tag)
        if ok:
            ok_count += 1
        else:
            fail_count += 1

    console.print(table)
    console.print(f"Verified: {ok_count} OK, {fail_count} failed")
    await conn.close()
