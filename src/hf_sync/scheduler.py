"""Scheduler — decides which file to process next.

Does NOT download, upload, or verify. Only plans.
"""

from __future__ import annotations

import asyncio

from loguru import logger

from hf_sync.engine.coordinator import Coordinator
from hf_sync.repositories.files import FileRepository
from hf_sync.types.dto import SyncTask


class Scheduler:
    """Pull pending files and feed them to the Coordinator."""

    coordinator: Coordinator
    repo: FileRepository
    interval: float

    def __init__(self, coordinator: Coordinator, repo: FileRepository, interval: float = 10.0) -> None:
        self.coordinator = coordinator
        self.repo = repo
        self.interval = interval

    async def run_cycle(self) -> bool:
        """Process one pending file. Return True if a file was processed."""
        row = await self.repo.get_pending()
        if row is None:
            return False

        task = SyncTask(
            file_id=int(row["id"]),
            filename=str(row["filename"]),
            source_url="",
            local_path=str(row["local_path"]),
            remote_path=str(row["remote_path"]),
            size=int(row["size"]),
            sha256=str(row["sha256"]),
        )
        await self.coordinator.run(task)
        return True

    async def loop(self) -> None:
        """Continuously process pending files until none remain."""
        logger.info("Scheduler started")
        while True:
            processed = await self.run_cycle()
            if not processed:
                pending = await self.repo.count_pending()
                if pending == 0:
                    logger.info("All files processed. Scheduler idle.")
                    break
                await asyncio.sleep(self.interval)
        logger.info("Scheduler finished")
