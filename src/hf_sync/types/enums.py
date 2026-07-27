"""Enumerations."""

from __future__ import annotations

from enum import Enum


class Status(str, Enum):
    """Possible states of a file in the pipeline."""

    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    DOWNLOADED = "DOWNLOADED"
    UPLOADING = "UPLOADING"
    VERIFYING = "VERIFYING"
    DONE = "DONE"
    FAILED = "FAILED"
