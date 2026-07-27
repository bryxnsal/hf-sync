"""Downloader — only talks to aria2.

Never knows about Google Drive or Hugging Face.
"""

from __future__ import annotations

from pathlib import Path

from hf_sync.services.aria2 import Aria2Service


class Downloader:
    """Handle file download via aria2."""

    aria2: Aria2Service

    def __init__(self, aria2: Aria2Service) -> None:
        self.aria2 = aria2

    def download(self, url: str, dest: str) -> str:
        """Download a file. Returns aria2 GID."""
        dest_dir = str(Path(dest).parent)
        gid = self.aria2.add_uri(url, {"dir": dest_dir, "out": Path(dest).name})
        return gid

    def wait_for_completion(self, gid: str, poll_interval: float = 2.0) -> dict[str, str]:
        """Poll aria2 until download completes or fails."""
        import time

        while True:
            status = self.aria2.tell_status(gid)
            s = status.get("status", "")
            if s in ("complete", "error", "removed"):
                return status
            time.sleep(poll_interval)
