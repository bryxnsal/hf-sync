"""Domain models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HFFile:
    """File metadata from Hugging Face."""

    filename: str
    size: int = 0
    sha256: str = ""
    download_url: str = ""


@dataclass
class DownloadTask:
    """Task representing a file to download."""

    file_id: int
    source_url: str
    dest_path: str
    size: int = 0
    gid: str = ""


@dataclass
class RepositoryInfo:
    """HF repository metadata."""

    repo_id: str
    files: list[HFFile] = field(default_factory=list)


@dataclass
class ProgressSnapshot:
    """Snapshot of current pipeline progress."""

    stage: str = ""
    current: int = 0
    total: int = 0
    elapsed: float = 0.0  # seconds
    file: str = ""
