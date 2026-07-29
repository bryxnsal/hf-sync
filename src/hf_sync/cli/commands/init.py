"""Init command — initialize DB and scan repo files."""
# pyright: reportCallInDefaultInitializer=false
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import typer
from loguru import logger

from hf_sync.cli.app import app, console
from hf_sync.config import settings
from hf_sync.database import Database
from hf_sync.logger import setup_logger
from hf_sync.repositories.files import FileRepository
from hf_sync.services.huggingface import HuggingFaceService


@app.command()
def init(
    repo_id: str = typer.Argument(
        default=None,
        help="HF repo ID (e.g. databricks/dolly-v2-3b). Optional if set in .env",
    ),
) -> None:
    """Initialize DB and scan repo files."""
    setup_logger(settings.log_level)
    asyncio.run(_init_impl(repo_id or settings.hf_repo_id))


async def _init_impl(repo_id: str) -> None:
    Path(settings.temp_dir).mkdir(parents=True, exist_ok=True)

    await Database.init_db(settings.db_path)
    logger.info("DB ready at {}", settings.db_path)

    if not settings.hf_token:
        console.print("[yellow]HF_TOKEN not set — skipping repo scan[/yellow]")
        return
    if not repo_id:
        console.print("[yellow]Specify a repo_id or set it in .env[/yellow]")
        return

    hf = HuggingFaceService(settings.hf_token)
    files = hf.list_files(repo_id)
    logger.info("Found {} files in {}", len(files), repo_id)

    conn = await Database(settings.db_path).connect()
    repo = FileRepository(conn)
    for f in files:
        fn: str = cast(str, f["filename"])
        _ = await repo.insert(
            filename=fn,
            size=int(cast(int, f.get("size", 0))),  # type: ignore[arg-type]
            status="PENDING",
            local_path=str(Path(settings.temp_dir) / fn),
        )
    await conn.close()
    console.print(f"[green]Scanned {len(files)} files — ready[/green]")
