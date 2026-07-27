"""Coordinator — orchestrates the full pipeline.

Downloader → Uploader → Verifier → Cleanup
"""

from __future__ import annotations

from loguru import logger

from hf_sync.engine.cleanup import Cleanup
from hf_sync.engine.downloader import Downloader
from hf_sync.engine.uploader import Uploader
from hf_sync.engine.verifier import Verifier
from hf_sync.repositories.files import FileRepository
from hf_sync.types.dto import SyncTask
from hf_sync.types.enums import Status


class Coordinator:
    """Coordinate one full sync cycle for a file."""

    def __init__(
        self,
        downloader: Downloader,
        uploader: Uploader,
        verifier: Verifier,
        cleanup: Cleanup,
        repo: FileRepository,
        temp_dir: str = "temp",
    ) -> None:
        self.downloader = downloader
        self.uploader = uploader
        self.verifier = verifier
        self.cleanup = cleanup
        self.repo = repo
        self.temp_dir = temp_dir

    async def run(self, task: SyncTask) -> bool:
        """Execute the pipeline for one file. Return True on success."""
        logger.info("Start sync for {}", task.filename)

        # --- DOWNLOAD ---
        logger.info("Downloading {} ...", task.filename)
        await self.repo.update_status(task.file_id, Status.DOWNLOADING)
        await self.repo.add_event(task.file_id, "download_start", task.source_url)

        try:
            gid = self.downloader.download(task.source_url, task.local_path)
            _last_pct = [0]

            def _dl_progress(completed: int, total: int, speed: int) -> None:
                if total > 0:
                    pct = int(completed / total * 100)
                    if pct >= _last_pct[0] + 10 or pct == 100:
                        _last_pct[0] = pct
                        from hf_sync.utils.bytes import human_size
                        logger.info("  {}% — {} / {} @ {}/s",
                                    pct, human_size(completed), human_size(total), human_size(speed))

            status = self.downloader.wait_for_completion(gid, progress_callback=_dl_progress)
            if status.get("status") != "complete":
                raise RuntimeError(f"aria2 failed: {status}")
        except Exception as e:
            logger.error("Download failed for {}: {}", task.filename, e)
            await self.repo.mark_failed(task.file_id)
            await self.repo.add_event(task.file_id, "download_fail", str(e))
            return False

        await self.repo.add_event(task.file_id, "download_done", task.local_path)
        logger.info("Downloaded {} OK", task.filename)

        # --- UPLOAD ---
        logger.info("Uploading {} ...", task.filename)
        await self.repo.update_status(task.file_id, Status.UPLOADING)
        await self.repo.add_event(task.file_id, "upload_start")

        try:
            remote = task.remote_path or f"{task.filename}"
            self.uploader.upload(task.local_path, remote)
        except Exception as e:
            logger.error("Upload failed for {}: {}", task.filename, e)
            await self.repo.mark_failed(task.file_id)
            await self.repo.add_event(task.file_id, "upload_fail", str(e))
            return False

        await self.repo.add_event(task.file_id, "upload_done", remote)
        logger.info("Uploaded {} OK", task.filename)

        # --- VERIFY ---
        logger.info("Verifying {} ...", task.filename)
        await self.repo.update_status(task.file_id, Status.VERIFYING)
        await self.repo.add_event(task.file_id, "verify_start")

        ok = self.verifier.verify(task.local_path, task.size, task.sha256)
        if not ok:
            logger.error("Verification failed for {}", task.filename)
            await self.repo.mark_failed(task.file_id)
            await self.repo.add_event(task.file_id, "verify_fail", "size/hash mismatch")
            return False

        await self.repo.add_event(task.file_id, "verify_done")
        logger.info("Verified {} OK", task.filename)

        # --- CLEANUP ---
        self.cleanup.remove_local(task.local_path)
        await self.repo.mark_done(task.file_id)
        await self.repo.add_event(task.file_id, "cleanup_done", task.local_path)

        logger.info("Done with {}", task.filename)
        return True
