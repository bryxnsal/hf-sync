"""Tests for CLI doctor command."""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

import pytest
from rich.console import Console
from typer.testing import CliRunner

from hf_sync.types.dto import DryRunReport


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestShowDryRun:
    """_show_dry_run prints a table and warnings."""

    def test_accessible_repo(self):
        from hf_sync.cli import _show_dry_run

        report = DryRunReport(
            repo_id="org/repo", destination="gdrive:path",
            repo_accessible=True, file_count=10, total_size=1_000_000,
            largest_file_name="big.bin", largest_file_size=500_000,
            local_free_gb=50.0, local_ok=True,
            dest_accessible=True, remote_free_gb=200.0, remote_ok=True,
        )
        buf = StringIO()
        with patch("hf_sync.cli.shared.display.DoctorService.dry_run", return_value=report):
            with patch("hf_sync.cli.shared.display.console", Console(file=buf, width=120, force_terminal=False)):
                _show_dry_run("org/repo", "gdrive:path")
        out = buf.getvalue()
        assert "Dry Run" in out
        assert "org/repo" in out
        assert "10" in out
        assert "big.bin" in out

    def test_inaccessible_repo_without_largest(self):
        from hf_sync.cli import _show_dry_run

        report = DryRunReport(
            repo_id="org/repo", repo_accessible=False,
            local_free_gb=10.0, local_ok=False,
            dest_accessible=False, remote_free_gb=0.0, remote_ok=False,
        )
        buf = StringIO()
        with patch("hf_sync.cli.shared.display.DoctorService.dry_run", return_value=report):
            with patch("hf_sync.cli.shared.display.console", Console(file=buf, width=120, force_terminal=False)):
                _show_dry_run("org/repo", "gdrive:bad")
        out = buf.getvalue()
        assert "Not enough local disk space" in out
        assert "Not enough space at destination" in out


class TestDoctorCommand:
    """Doctor command via CliRunner."""

    def test_doctor_basic(self, cli_runner):
        from hf_sync.cli import app
        from hf_sync.types.dto import DoctorReport

        report = DoctorReport(aria2=True, rclone=True, hf_token=True,
                              drive_access=True, free_space_gb=50.0, permissions_ok=True)
        with patch("hf_sync.cli.commands.doctor.DoctorService") as mock_svc:
            mock_svc.return_value.check_all.return_value = report
            result = cli_runner.invoke(app, ["doctor"])
        assert result.exit_code == 0

    def test_doctor_with_args(self, cli_runner):
        from hf_sync.cli import app

        with patch("hf_sync.cli.commands.doctor._show_dry_run"):
            result = cli_runner.invoke(app, ["doctor", "org/repo", "gdrive:path"])
        assert result.exit_code == 0

    def test_doctor_with_hints(self, cli_runner):
        from hf_sync.cli import app
        from hf_sync.types.dto import DoctorReport

        report = DoctorReport(aria2=False, aria2_error="refused",
                              rclone=True, hf_token=False, hf_token_configured=False,
                              drive_configured=False, free_space_gb=0.0, permissions_ok=True)
        with patch("hf_sync.cli.commands.doctor.DoctorService") as mock_svc:
            mock_svc.return_value.check_all.return_value = report
            result = cli_runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "aria2" in result.output.lower()

    def test_doctor_drive_not_configured(self, cli_runner):
        from hf_sync.cli import app
        from hf_sync.types.dto import DoctorReport

        report = DoctorReport(aria2=True, rclone=True, hf_token=True,
                              hf_token_configured=True,
                              drive_configured=False, drive_access=False,
                              free_space_gb=0.0, permissions_ok=True)
        with patch("hf_sync.cli.commands.doctor.DoctorService") as mock_svc:
            mock_svc.return_value.check_all.return_value = report
            result = cli_runner.invoke(app, ["doctor"])
        assert result.exit_code == 0

    def test_doctor_drive_error_hint(self, cli_runner):
        from hf_sync.cli import app
        from hf_sync.types.dto import DoctorReport

        report = DoctorReport(
            aria2=True, rclone=True, hf_token=True, hf_token_configured=True,
            drive_configured=True, drive_access=False, drive_error="remote not found",
            free_space_gb=0.0, permissions_ok=True,
        )
        with patch("hf_sync.cli.commands.doctor.DoctorService") as mock_svc:
            mock_svc.return_value.check_all.return_value = report
            result = cli_runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "remote not found" in result.output
