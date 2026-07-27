"""Data transfer objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SyncTask:
    """DTO that flows through the pipeline."""

    file_id: int
    filename: str
    source_url: str
    local_path: str
    remote_path: str
    size: int = 0
    sha256: str = ""
    status: str = "PENDING"


@dataclass
class RepoInfoDTO:
    """DTO for repository metadata returned by doctor."""

    repo_id: str
    file_count: int = 0
    total_size: int = 0
    accessible: bool = False


@dataclass
class DoctorReport:
    """DTO for system health check results."""

    aria2: bool = False
    rclone: bool = False
    hf_token: bool = False
    drive_access: bool = False
    free_space_gb: float = 0.0
    permissions_ok: bool = False


@dataclass
class DryRunReport:
    """DTO for pre-flight / dry-run results."""

    repo_id: str = ""
    destination: str = ""
    repo_accessible: bool = False
    file_count: int = 0
    total_size: int = 0
    largest_file_name: str = ""
    largest_file_size: int = 0
    local_free_gb: float = 0.0
    local_ok: bool = False
    dest_accessible: bool = False
    remote_free_gb: float = 0.0
    remote_ok: bool = False
