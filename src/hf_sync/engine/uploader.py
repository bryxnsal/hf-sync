"""Uploader — only talks to rclone.

Never knows about Hugging Face.
"""

from __future__ import annotations

from hf_sync.services.rclone import RcloneService


class Uploader:
    """Handle file upload via rclone."""

    def __init__(self, rclone: RcloneService) -> None:
        self.rclone = rclone

    def upload(self, local_path: str, remote_dest: str) -> None:
        """Upload a file to the configured remote."""
        self.rclone.copyto(local_path, remote_dest)
