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

    async def run(self, task: SyncTask, progress_callback=None) -> tuple[bool, str]:
        """Execute the pipeline for one file. Return (success, error_msg).

        If progress_callback is provided, it is called with
        (stage: str, pct: float, speed: str) at each phase.
        Stages: "download", "upload", "verify".
        """
        if progress_callback:
            progress_callback("download", 0, "")

        await self.repo.update_status(task.file_id, Status.DOWNLOADING)
        await self.repo.add_event(task.file_id, "download_start", task.source_url)

        # --- DOWNLOAD ---
        try:
            gid = self.downloader.download(task.source_url, task.local_path)

            def _dl_progress(completed: int, total: int, speed: int) -> None:
                pct = (completed / total * 100) if total else 0
                if progress_callback:
                    from hf_sync.utils.bytes import human_size
                    spd = f"{human_size(speed)}/s" if speed else ""
                    progress_callback("download", pct, spd)

            status = self.downloader.wait_for_completion(gid, progress_callback=_dl_progress)
            if status.get("status") != "complete":
                raise RuntimeError(f"aria2 failed: {status}")
        except Exception as e:
            logger.error("Download failed for {}: {}", task.filename, e)
            self.cleanup.remove_local(task.local_path)
            await self.repo.mark_failed(task.file_id)
            await self.repo.add_event(task.file_id, "download_fail", str(e))
            return False, str(e)

        await self.repo.add_event(task.file_id, "download_done", task.local_path)
        if progress_callback:
            progress_callback("download", 100, "")

        # --- UPLOAD ---
        await self.repo.update_status(task.file_id, Status.UPLOADING)
        await self.repo.add_event(task.file_id, "upload_start")
        if progress_callback:
            progress_callback("upload", 0, "")

        try:
            remote = task.remote_path or f"{task.filename}"
            await self.uploader.upload(task.local_path, remote, progress_callback=progress_callback)
        except Exception as e:
            logger.error("Upload failed for {}: {}", task.filename, e)
            self.cleanup.remove_local(task.local_path)
            await self.repo.mark_failed(task.file_id)
            await self.repo.add_event(task.file_id, "upload_fail", str(e))
            return False, str(e)

        await self.repo.add_event(task.file_id, "upload_done", remote)
        if progress_callback:
            progress_callback("upload", 100, "")

        # --- VERIFY ---
        await self.repo.update_status(task.file_id, Status.VERIFYING)
        await self.repo.add_event(task.file_id, "verify_start")
        if progress_callback:
            progress_callback("verify", 0, "")

        ok = self.verifier.verify(task.local_path, task.size, task.sha256)
        if not ok:
            logger.error("Verification failed for {}", task.filename)
            self.cleanup.remove_local(task.local_path)
            await self.repo.mark_failed(task.file_id)
            await self.repo.add_event(task.file_id, "verify_fail", "size/hash mismatch")
            return False, "Verification failed: size/hash mismatch"

        await self.repo.add_event(task.file_id, "verify_done")
        if progress_callback:
            progress_callback("verify", 100, "")

        # --- CLEANUP ---
        self.cleanup.remove_local(task.local_path)
        await self.repo.mark_done(task.file_id)
        await self.repo.add_event(task.file_id, "cleanup_done", task.local_path)

        return True, ""
