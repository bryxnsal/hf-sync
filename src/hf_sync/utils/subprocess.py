"""Subprocess utilities."""

from __future__ import annotations

import subprocess
from typing import Any


def run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """Run a command and return result."""
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)  # type: ignore[return-value]
