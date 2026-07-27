"""Cleanup — removes temp files, updates DB state."""

from __future__ import annotations

from pathlib import Path


class Cleanup:
    """Remove processed temp files after successful upload + verify."""

    @staticmethod
    def remove_local(path: str) -> None:
        """Delete the local temp file."""
        p = Path(path)
        if p.is_file():
            p.unlink()
