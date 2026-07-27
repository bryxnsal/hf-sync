"""Health check and dry-run service."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from hf_sync.config import settings
from hf_sync.services.aria2 import Aria2Service
from hf_sync.services.huggingface import HuggingFaceService
from hf_sync.services.rclone import RcloneService
from hf_sync.types.dto import DoctorReport, DryRunReport


class DoctorService:
    """System diagnostics."""

    def check_all(self) -> DoctorReport:
        """Run all system health checks."""
        report = DoctorReport()

        try:
            aria2 = Aria2Service(settings.aria2_rpc_url, settings.aria2_rpc_secret)
            aria2.tell_status("0" * 16)
            report.aria2 = True
        except Exception:
            report.aria2 = False

        report.rclone = shutil.which("rclone") is not None

        if settings.hf_token:
            try:
                hf = HuggingFaceService(settings.hf_token)
                hf.repo_info("gpt2")
                report.hf_token = True
            except Exception:
                report.hf_token = False

        remote = settings.rclone_remote
        if remote:
            rclone = RcloneService(remote)
            try:
                rclone.lsjson(f"{remote}:")
                report.drive_access = True
            except Exception:
                report.drive_access = False
            try:
                report.free_space_gb = rclone.free_space(f"{remote}:")
            except Exception:
                report.free_space_gb = 0.0

        for d in ("data", "temp"):
            p = Path(d)
            p.mkdir(parents=True, exist_ok=True)
            if not os.access(p, os.W_OK):
                report.permissions_ok = False
                break
        else:
            report.permissions_ok = True

        return report

    @staticmethod
    def dry_run(repo_id: str, destination: str = "") -> DryRunReport:
        """Pre-flight checks: repo access, largest file, local & remote space."""
        report = DryRunReport(repo_id=repo_id, destination=destination)

        # Repo access
        if settings.hf_token:
            try:
                hf = HuggingFaceService(settings.hf_token)
                info = hf.repo_info(repo_id)
                report.repo_accessible = True
                files = hf.list_files(repo_id)
                report.file_count = len(files)
                report.total_size = sum(f.get("size", 0) or 0 for f in files)
                for f in files:
                    sz = int(f.get("size", 0) or 0)
                    if sz > report.largest_file_size:
                        report.largest_file_size = sz
                        report.largest_file_name = str(f["filename"])
            except Exception:
                report.repo_accessible = False

        # Local disk
        temp_path = Path(settings.temp_dir)
        temp_path.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(temp_path)
        report.local_free_gb = round(usage.free / (1024**3), 2)
        check_size = report.largest_file_size or 1024**3
        report.local_ok = usage.free > check_size

        # Remote space
        remote_part, _ = _parse_destination(destination) if destination else (settings.rclone_remote, "")
        if remote_part:
            rclone = RcloneService(remote_part)
            try:
                rclone.lsjson(f"{remote_part}:")
                report.dest_accessible = True
            except Exception:
                report.dest_accessible = False
            try:
                report.remote_free_gb = rclone.free_space(f"{remote_part}:")
                report.remote_ok = report.remote_free_gb * (1024**3) > check_size
            except Exception:
                report.remote_free_gb = 0.0
                report.remote_ok = False

        return report


def _parse_destination(dest: str) -> tuple[str, str]:
    if ":" in dest:
        parts = dest.split(":", 1)
        return parts[0], parts[1]
    return dest, ""
