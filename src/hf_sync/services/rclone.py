"""Rclone subprocess wrapper.

Methods: copyto, lsjson, delete, exists.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any


class RcloneService:
    """Thin wrapper around the rclone binary."""

    remote: str

    def __init__(self, remote: str = "", path: str = "") -> None:
        self.remote = remote

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        cmd = ["rclone", *args]
        return subprocess.run(cmd, capture_output=True, text=True)

    def copyto(self, src: str, dest: str) -> None:
        """Copy a file to remote."""
        result = self._run(["copyto", src, dest])
        if result.returncode != 0:
            raise RuntimeError(f"rclone copyto failed: {result.stderr.strip()}")

    def lsjson(self, remote_path: str) -> list[dict[str, Any]]:
        """List files at remote path as JSON."""
        result = self._run(["lsjson", remote_path])
        if result.returncode != 0:
            return []
        return json.loads(result.stdout) if result.stdout.strip() else []

    def delete(self, remote_path: str) -> None:
        """Delete a single file from remote."""
        self._run(["deletefile", remote_path])

    def exists(self, remote_path: str) -> bool:
        """Check if a file exists on remote."""
        result = self._run(["lsjson", remote_path])
        return result.returncode == 0 and bool(result.stdout.strip())

    def free_space(self, remote_path: str) -> float:
        """Return free space on remote mount in GB."""
        result = self._run(["about", remote_path, "--json"])
        if result.returncode != 0:
            return 0.0
        data: dict[str, Any] = json.loads(result.stdout)
        free_bytes = data.get("free", 0)
        return round(float(free_bytes) / (1024**3), 2)
