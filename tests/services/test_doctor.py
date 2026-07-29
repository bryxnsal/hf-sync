"""Tests for DoctorService — health checks and dry-run."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from hf_sync.services.doctor import DoctorService, _parse_destination
from hf_sync.types.dto import DoctorReport


class TestParseDestination:
    def test_with_colon(self):
        r, p = _parse_destination("gdrive:path/to/model")
        assert r == "gdrive"
        assert p == "path/to/model"

    def test_remote_only(self):
        r, p = _parse_destination("gdrive")
        assert r == "gdrive"
        assert p == ""

    def test_empty(self):
        r, p = _parse_destination("")
        assert r == ""
        assert p == ""


class TestCheckAria2:
    @patch("hf_sync.services.doctor.settings")
    @patch("hf_sync.services.doctor.Aria2Service")
    def test_success(self, mock_aria2_cls, mock_settings):
        mock_settings.aria2_rpc_url = "http://localhost:6800/jsonrpc"
        mock_settings.aria2_rpc_secret = ""
        mock_aria2 = MagicMock()
        mock_aria2_cls.return_value = mock_aria2
        report = DoctorReport()
        DoctorService._check_aria2(report)
        assert report.aria2 is True
        assert report.aria2_error == ""

    @patch("hf_sync.services.doctor.settings")
    @patch("hf_sync.services.doctor.Aria2Service")
    def test_connection_refused(self, mock_aria2_cls, mock_settings):
        mock_settings.aria2_rpc_url = "http://localhost:6800/jsonrpc"
        mock_settings.aria2_rpc_secret = ""
        mock_aria2 = MagicMock()
        mock_aria2.get_version.side_effect = httpx.ConnectError("refused")
        mock_aria2_cls.return_value = mock_aria2
        report = DoctorReport()
        DoctorService._check_aria2(report)
        assert report.aria2 is False
        assert "refused" in report.aria2_error

    @patch("hf_sync.services.doctor.settings")
    @patch("hf_sync.services.doctor.Aria2Service")
    def test_timeout(self, mock_aria2_cls, mock_settings):
        mock_settings.aria2_rpc_url = "http://localhost:6800/jsonrpc"
        mock_settings.aria2_rpc_secret = ""
        mock_aria2 = MagicMock()
        mock_aria2.get_version.side_effect = httpx.TimeoutException("timed out")
        mock_aria2_cls.return_value = mock_aria2
        report = DoctorReport()
        DoctorService._check_aria2(report)
        assert report.aria2 is False

    @patch("hf_sync.services.doctor.settings")
    @patch("hf_sync.services.doctor.Aria2Service")
    def test_runtime_error(self, mock_aria2_cls, mock_settings):
        mock_settings.aria2_rpc_url = "http://localhost:6800/jsonrpc"
        mock_settings.aria2_rpc_secret = ""
        mock_aria2 = MagicMock()
        mock_aria2.get_version.side_effect = RuntimeError("RPC error")
        mock_aria2_cls.return_value = mock_aria2
        report = DoctorReport()
        DoctorService._check_aria2(report)
        assert report.aria2 is False

    @patch("hf_sync.services.doctor.settings")
    @patch("hf_sync.services.doctor.Aria2Service")
    def test_generic_exception(self, mock_aria2_cls, mock_settings):
        mock_settings.aria2_rpc_url = "http://localhost:6800/jsonrpc"
        mock_settings.aria2_rpc_secret = ""
        mock_aria2 = MagicMock()
        mock_aria2.get_version.side_effect = PermissionError("no perms")
        mock_aria2_cls.return_value = mock_aria2
        report = DoctorReport()
        DoctorService._check_aria2(report)
        assert report.aria2 is False
        assert "no perms" in report.aria2_error

    @patch("hf_sync.services.doctor.settings")
    @patch("hf_sync.services.doctor.Aria2Service")
    def test_fallback_to_127_0_0_1(self, mock_aria2_cls, mock_settings):
        mock_settings.aria2_rpc_url = "http://localhost:6800/jsonrpc"
        mock_settings.aria2_rpc_secret = ""
        mock_aria2 = MagicMock()
        mock_aria2_cls.return_value = mock_aria2
        # First call (localhost) fails, second (127.0.0.1) succeeds
        mock_aria2.get_version.side_effect = [
            httpx.ConnectError("refused"),
            {"version": "1.37.0"},
        ]
        report = DoctorReport()
        DoctorService._check_aria2(report)
        assert report.aria2 is True
        assert mock_aria2_cls.call_count == 2
        urls = [c[0][0] for c in mock_aria2_cls.call_args_list]
        assert "127.0.0.1" in urls[1]


class TestCheckRcloneRemotes:
    @patch("subprocess.run")
    def test_found(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="gdrive:\nother:\n", stderr=""
        )
        result = DoctorService._check_rclone_remotes()
        assert result == "gdrive"

    @patch("subprocess.run")
    def test_empty(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = DoctorService._check_rclone_remotes()
        assert result == ""

    @patch("subprocess.run")
    def test_failure(self, mock_run):
        mock_run.side_effect = RuntimeError("rclone not found")
        result = DoctorService._check_rclone_remotes()
        assert result == ""


class TestCheckAll:
    @patch("hf_sync.services.doctor.DoctorService._check_aria2")
    @patch("hf_sync.services.doctor.settings")
    @patch("shutil.which")
    def test_basic_checks(self, mock_which, mock_settings, mock_check_aria2):
        mock_which.return_value = "/usr/bin/rclone"
        mock_settings.hf_token = "hf_test"
        mock_settings.aria2_rpc_url = "http://localhost:6800/jsonrpc"
        mock_settings.aria2_rpc_secret = ""
        mock_settings.rclone_remote = "gdrive"
        mock_settings.db_path = "/tmp/hf-sync-test/state.db"
        mock_settings.temp_dir = "/tmp/hf-sync-test/temp"

        svc = DoctorService()
        report = svc.check_all()

        assert report.rclone is True
        mock_check_aria2.assert_called_once()

    @patch("hf_sync.services.doctor.DoctorService._check_aria2")
    @patch("hf_sync.services.doctor.settings")
    @patch("shutil.which")
    def test_hf_token_not_configured(self, mock_which, mock_settings, mock_check_aria2):
        mock_which.return_value = "/usr/bin/rclone"
        mock_settings.hf_token = ""
        mock_settings.aria2_rpc_url = "http://localhost:6800/jsonrpc"
        mock_settings.aria2_rpc_secret = ""
        mock_settings.rclone_remote = "gdrive"
        mock_settings.db_path = "/tmp/hf-sync-test/state.db"
        mock_settings.temp_dir = "/tmp/hf-sync-test/temp"

        svc = DoctorService()
        report = svc.check_all()
        assert report.hf_token_configured is False

    @patch("hf_sync.services.doctor.DoctorService._check_aria2")
    @patch("hf_sync.services.doctor.settings")
    @patch("shutil.which")
    def test_drive_access_failure(self, mock_which, mock_settings, mock_check_aria2):
        mock_which.return_value = "/usr/bin/rclone"
        mock_settings.hf_token = ""
        mock_settings.aria2_rpc_url = "http://localhost:6800/jsonrpc"
        mock_settings.aria2_rpc_secret = ""
        mock_settings.rclone_remote = "gdrive"
        mock_settings.db_path = "/tmp/hf-sync-test/state.db"
        mock_settings.temp_dir = "/tmp/hf-sync-test/temp"

        with patch("hf_sync.services.doctor.RcloneService") as mock_rclone_cls:
            mock_rclone = MagicMock()
            mock_rclone_cls.return_value = mock_rclone
            mock_rclone.lsjson.side_effect = RuntimeError("rclone crash")

            svc = DoctorService()
            report = svc.check_all()
            assert report.drive_access is False
            assert "rclone crash" in report.drive_error

    @patch("hf_sync.services.doctor.DoctorService._check_aria2")
    @patch("hf_sync.services.doctor.settings")
    @patch("shutil.which")
    def test_free_space_failure(self, mock_which, mock_settings, mock_check_aria2):
        mock_which.return_value = "/usr/bin/rclone"
        mock_settings.hf_token = ""
        mock_settings.aria2_rpc_url = "http://localhost:6800/jsonrpc"
        mock_settings.aria2_rpc_secret = ""
        mock_settings.rclone_remote = "gdrive"
        mock_settings.db_path = "/tmp/hf-sync-test/state.db"
        mock_settings.temp_dir = "/tmp/hf-sync-test/temp"

        with patch("hf_sync.services.doctor.RcloneService") as mock_rclone_cls:
            mock_rclone = MagicMock()
            mock_rclone_cls.return_value = mock_rclone
            mock_rclone.lsjson.return_value = []
            mock_rclone.free_space.side_effect = RuntimeError("no space cmd")

            svc = DoctorService()
            report = svc.check_all()
            assert report.free_space_gb == 0.0

    @patch("hf_sync.services.doctor.DoctorService._check_aria2")
    @patch("hf_sync.services.doctor.settings")
    @patch("shutil.which")
    def test_drive_not_configured_branch(self, mock_which, mock_settings, mock_check_aria2):
        """Cover the else branch: drive_configured = False when no remote."""
        mock_which.return_value = "/usr/bin/rclone"
        mock_settings.hf_token = ""
        mock_settings.aria2_rpc_url = "http://localhost:6800/jsonrpc"
        mock_settings.aria2_rpc_secret = ""
        mock_settings.rclone_remote = ""
        mock_settings.rclone_path = ""
        mock_settings.db_path = "/tmp/hf-sync-test/state.db"
        mock_settings.temp_dir = "/tmp/hf-sync-test/temp"

        # _check_rclone_remotes returns empty too
        with patch.object(DoctorService, "_check_rclone_remotes", return_value=""):
            svc = DoctorService()
            report = svc.check_all()
            assert report.drive_configured is False

    @patch("hf_sync.services.doctor.DoctorService._check_aria2")
    @patch("hf_sync.services.doctor.settings")
    @patch("shutil.which")
    def test_permissions_failure(self, mock_which, mock_settings, mock_check_aria2):
        mock_which.return_value = "/usr/bin/rclone"
        mock_settings.hf_token = ""
        mock_settings.aria2_rpc_url = "http://localhost:6800/jsonrpc"
        mock_settings.aria2_rpc_secret = ""
        mock_settings.rclone_remote = "gdrive"
        mock_settings.db_path = "/tmp/hf-sync-test/nonexistent/state.db"
        mock_settings.temp_dir = "/tmp"

        # Make data_dir non-writable by using a path we can't write to
        with patch("os.access", return_value=False):
            svc = DoctorService()
            report = svc.check_all()
            assert report.permissions_ok is False

    @patch("hf_sync.services.doctor.DoctorService._check_aria2")
    @patch("hf_sync.services.doctor.settings")
    @patch("shutil.which")
    def test_no_remote_configured_detects(self, mock_which, mock_settings, mock_check_aria2):
        mock_which.return_value = "/usr/bin/rclone"
        mock_settings.hf_token = ""
        mock_settings.aria2_rpc_url = "http://localhost:6800/jsonrpc"
        mock_settings.aria2_rpc_secret = ""
        mock_settings.rclone_remote = ""
        mock_settings.db_path = "/tmp/hf-sync-test/state.db"
        mock_settings.temp_dir = "/tmp/hf-sync-test/temp"

        with patch.object(DoctorService, "_check_rclone_remotes", return_value="auto_detect"):
            with patch("hf_sync.services.doctor.RcloneService") as mock_rclone_cls:
                mock_rclone = MagicMock()
                mock_rclone_cls.return_value = mock_rclone
                mock_rclone.lsjson.return_value = []
                mock_rclone.free_space.return_value = 50.0

                svc = DoctorService()
                report = svc.check_all()
                assert report.drive_configured is True
                assert "Set RCLONE_REMOTE" in report.drive_error

    @patch("hf_sync.services.doctor.DoctorService._check_aria2")
    @patch("hf_sync.services.doctor.settings")
    @patch("shutil.which")
    def test_hf_token_failure(self, mock_which: MagicMock, mock_settings: MagicMock, mock_check_aria2: MagicMock) -> None:  # pyright: ignore[reportUnusedParameter]
        mock_which.return_value = "/usr/bin/rclone"
        mock_settings.hf_token = "hf_bad"
        mock_settings.aria2_rpc_url = "http://localhost:6800/jsonrpc"
        mock_settings.aria2_rpc_secret = ""
        mock_settings.rclone_remote = "gdrive"
        mock_settings.db_path = "/tmp/hf-sync-test/state.db"
        mock_settings.temp_dir = "/tmp/hf-sync-test/temp"

        with patch("hf_sync.services.doctor.HuggingFaceService") as mock_hf_cls:
            mock_hf = MagicMock()
            mock_hf_cls.return_value = mock_hf
            mock_hf.repo_info.side_effect = RuntimeError("API error")

            svc = DoctorService()
            report = svc.check_all()
            assert report.hf_token is False

    @patch("hf_sync.services.doctor.DoctorService._check_aria2")
    @patch("hf_sync.services.doctor.settings")
    @patch("shutil.which")
    def test_permissions_ok(self, mock_which: MagicMock, mock_settings: MagicMock, mock_check_aria2: MagicMock) -> None:  # pyright: ignore[reportUnusedParameter]
        mock_which.return_value = "/usr/bin/rclone"
        mock_settings.hf_token = ""
        mock_settings.aria2_rpc_url = "http://localhost:6800/jsonrpc"
        mock_settings.aria2_rpc_secret = ""
        mock_settings.rclone_remote = "gdrive"
        mock_settings.db_path = "/tmp/hf-sync-test/state.db"
        mock_settings.temp_dir = "/tmp/hf-sync-test/temp"

        with patch("hf_sync.services.doctor.RcloneService") as mock_rclone_cls:
            mock_rclone = MagicMock()
            mock_rclone_cls.return_value = mock_rclone
            mock_rclone.lsjson.return_value = []
            mock_rclone.free_space.return_value = 50.0

            svc = DoctorService()
            report = svc.check_all()
            assert report.permissions_ok is True


class TestDryRun:
    @patch("hf_sync.services.doctor.settings")
    def test_report_defaults(self, mock_settings: MagicMock) -> None:
        mock_settings.hf_token = ""
        mock_settings.temp_dir = "/tmp/hf-sync-test"

        report = DoctorService.dry_run("org/repo")

        assert report.repo_id == "org/repo"
        assert report.repo_accessible is False
        assert report.file_count == 0
        assert report.local_free_gb > 0

    @patch("hf_sync.services.doctor.settings")
    def test_repo_not_accessible(self, mock_settings: MagicMock) -> None:
        mock_settings.hf_token = "hf_bad"
        mock_settings.temp_dir = "/tmp/hf-sync-test"

        with patch("hf_sync.services.doctor.HuggingFaceService") as mock_hf_cls:
            mock_hf = MagicMock()
            mock_hf_cls.return_value = mock_hf
            mock_hf.repo_info.side_effect = RuntimeError("not found")

            report = DoctorService.dry_run("org/nonexistent")
            assert report.repo_accessible is False

    @patch("hf_sync.services.doctor.settings")
    def test_with_hf_token_and_files(self, mock_settings: MagicMock) -> None:
        mock_settings.hf_token = "hf_test"
        mock_settings.temp_dir = "/tmp/hf-sync-test"

        with patch("hf_sync.services.doctor.HuggingFaceService") as mock_hf_cls:
            mock_hf = MagicMock()
            mock_hf_cls.return_value = mock_hf
            mock_hf.repo_info.return_value = {"id": "org/repo", "private": False}
            mock_hf.list_files.return_value = [
                {"filename": "small.bin", "size": 100},
                {"filename": "big.bin", "size": 1_000_000_000},
            ]

            report = DoctorService.dry_run("org/repo")
            assert report.repo_accessible is True
            assert report.file_count == 2
            assert report.total_size == 1_000_000_100
            assert report.largest_file_name == "big.bin"
            assert report.largest_file_size == 1_000_000_000

    @patch("hf_sync.services.doctor.settings")
    def test_dest_not_accessible(self, mock_settings: MagicMock) -> None:
        mock_settings.hf_token = ""
        mock_settings.temp_dir = "/tmp/hf-sync-test"
        mock_settings.rclone_remote = ""

        with patch("hf_sync.services.doctor.RcloneService") as mock_rclone_cls:
            mock_rclone = MagicMock()
            mock_rclone_cls.return_value = mock_rclone
            mock_rclone.lsjson.side_effect = RuntimeError("bad remote")

            report = DoctorService.dry_run("org/repo", "badremote:path")
            assert report.dest_accessible is False

    @patch("hf_sync.services.doctor.settings")
    def test_remote_space_failure(self, mock_settings: MagicMock) -> None:
        mock_settings.hf_token = ""
        mock_settings.temp_dir = "/tmp/hf-sync-test"
        mock_settings.rclone_remote = ""

        with patch("hf_sync.services.doctor.RcloneService") as mock_rclone_cls:
            mock_rclone = MagicMock()
            mock_rclone_cls.return_value = mock_rclone
            mock_rclone.lsjson.return_value = []
            mock_rclone.free_space.side_effect = RuntimeError("no space")

            report = DoctorService.dry_run("org/repo", "gdrive:path")
            assert report.remote_free_gb == 0.0
            assert report.remote_ok is False

    @patch("hf_sync.services.doctor.settings")
    def test_with_destination(self, mock_settings: MagicMock) -> None:
        mock_settings.hf_token = ""
        mock_settings.temp_dir = "/tmp/hf-sync-test"
        mock_settings.rclone_remote = ""

        with patch("hf_sync.services.doctor.RcloneService") as mock_rclone_cls:
            mock_rclone = MagicMock()
            mock_rclone_cls.return_value = mock_rclone
            mock_rclone.lsjson.return_value = []
            mock_rclone.free_space.return_value = 100.0

            report = DoctorService.dry_run("org/repo", "gdrive:models/llama")
            assert report.destination == "gdrive:models/llama"
