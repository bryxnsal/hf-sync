"""Uploader — only talks to rclone.

Never knows about Hugging Face.
"""

from __future__ import annotations

from hf_sync.services.rclone import RcloneService


class Uploader:
    """Handle file upload via rclone."""

    def __init__(self, rclone: RcloneService) -> None:
        self.rclone = rclone

    async def upload(self, local_path: str, remote_dest: str, progress_callback=None) -> None:
        """Upload a file to the configured remote."""
        await self.rclone.copyto_async(local_path, remote_dest, progress_callback=progress_callback)
