"""Rclone subprocess wrapper.

Methods: copyto, lsjson, delete, exists.
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
from collections.abc import Callable
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
        """Copy a file to remote (sync fallback)."""
        result = self._run(["copyto", src, dest])
        if result.returncode != 0:
            raise RuntimeError(f"rclone copyto failed: {result.stderr.strip()}")

    async def copyto_async(self, src: str, dest: str, progress_callback: Callable[[str, float, str], None] | None = None) -> None:
        """Copy a file to remote with real-time progress via --stats=1s."""
        if not progress_callback:
            self.copyto(src, dest)
            return

        process = await asyncio.create_subprocess_exec(
            "rclone", "copyto", src, dest,
            "--stats=1s",
            stderr=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
        )

        pct_re = re.compile(r"(\d+)%")
        speed_re = re.compile(r"([\d.]+)\s*([KMGT]i?B)/s")
        assert process.stderr is not None
        stderr_lines: list[str] = []

        while True:
            line = await process.stderr.readline()
            if not line:
                break
            decoded = line.decode(errors="replace").rstrip("\r\n")
            stderr_lines.append(decoded)
            m = pct_re.search(decoded)
            if m:
                pct = float(m.group(1))
                speed = ""
                s = speed_re.search(decoded)
                if s:
                    speed = f"{s.group(1)}{s.group(2)}/s"
                progress_callback("upload", pct, speed)

        await process.wait()
        if process.returncode != 0:
            err = "\n".join(stderr_lines[-5:])
            raise RuntimeError(f"rclone copyto failed: {err}")

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
