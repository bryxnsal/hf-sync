"""Uploader — only talks to rclone.

Never knows about Hugging Face.
"""

from __future__ import annotations

from hf_sync.services.rclone import RcloneService
from hf_sync.types.dto import ProgressCallback as _CB


class Uploader:
    """Handle file upload via rclone."""

    def __init__(self, rclone: RcloneService) -> None:
        self.rclone: RcloneService = rclone

    async def upload(self, local_path: str, remote_dest: str, progress_callback: _CB = None) -> None:
        """Upload a file to the configured remote."""
        await self.rclone.copyto_async(local_path, remote_dest, progress_callback=progress_callback)
