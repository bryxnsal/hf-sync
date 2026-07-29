"""Tests for CLI — display components and command dispatch."""

from __future__ import annotations

import subprocess
import sys
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console

from hf_sync.cli import _fmt_elapsed, _FrozenBar


class TestFmtElapsed:
    def test_seconds(self):
        assert _fmt_elapsed(0) == "0:00"
        assert _fmt_elapsed(5) == "0:05"
        assert _fmt_elapsed(59) == "0:59"

    def test_minutes(self):
        assert _fmt_elapsed(60) == "1:00"
        assert _fmt_elapsed(3599) == "59:59"

    def test_hours(self):
        assert _fmt_elapsed(3600) == "1:00:00"
        assert _fmt_elapsed(3661) == "1:01:01"
        assert _fmt_elapsed(86399) == "23:59:59"


class TestFrozenBar:
    def test_success_renders_all_fields(self):
        bar = _FrozenBar(1, 54, "model.safetensors", "15.8GB", "1:23:45", "OK", True)
        buf = StringIO()
        c = Console(file=buf, width=120, force_terminal=False)
        c.print(bar)
        out = buf.getvalue()
        assert "[1/54]" in out
        assert "model.safetensors" in out
        assert "15.8GB" in out
        assert "100%" in out
        assert "1:23:45" in out
        assert "OK" in out

    def test_error_renders_message_no_pct(self):
        bar = _FrozenBar(2, 54, "bad.bin", "1.2GB", "0:00:15", "Connection refused", False)
        buf = StringIO()
        c = Console(file=buf, width=120, force_terminal=False)
        c.print(bar)
        out = buf.getvalue()
        assert "[2/54]" in out
        assert "bad.bin" in out
        assert "1.2GB" in out
        assert "0:00:15" in out
        assert "Connection refused" in out
        assert "100" not in out

    def test_success_color_green(self):
        bar = _FrozenBar(1, 1, "f", "1B", "0:01", "OK", True)
        buf = StringIO()
        c = Console(file=buf, width=80, force_terminal=True, color_system="standard")
        c.print(bar)
        assert "\x1b[32m" in buf.getvalue()

    def test_error_color_red(self):
        bar = _FrozenBar(1, 1, "f", "1B", "0:01", "fail", False)
        buf = StringIO()
        c = Console(file=buf, width=80, force_terminal=True, color_system="standard")
        c.print(bar)
        assert "\x1b[31m" in buf.getvalue()

    def test_success_emoji(self):
        bar = _FrozenBar(1, 1, "f", "1B", "0:01", "OK", True)
        buf = StringIO()
        c = Console(file=buf, width=80, force_terminal=False)
        c.print(bar)
        assert "✓" in buf.getvalue()

    def test_error_emoji(self):
        bar = _FrozenBar(1, 1, "f", "1B", "0:01", "fail", False)
        buf = StringIO()
        c = Console(file=buf, width=80, force_terminal=False)
        c.print(bar)
        assert "✗" in buf.getvalue()

    def test_narrow_width_truncates(self):
        bar = _FrozenBar(1, 100, "very-long-filename.bin", "15.8GB", "1:00:00", "OK", True)
        buf = StringIO()
        c = Console(file=buf, width=40, force_terminal=False)
        c.print(bar)  # should not crash
        assert buf.getvalue()


@pytest.fixture
def cli_runner():
    from typer.testing import CliRunner

    return CliRunner()


# ── _parse_destination ────────────────────────────────────────────────


class TestParseDestination:
    """_parse_destination splits remote:path."""

    def test_with_colon(self):
        from hf_sync.cli import _parse_destination

        r, p = _parse_destination("gdrive:path/to/model")
        assert r == "gdrive"
        assert p == "path/to/model"

    def test_remote_only(self):
        from hf_sync.cli import _parse_destination

        r, p = _parse_destination("gdrive")
        assert r == "gdrive"
        assert p == ""

    def test_empty(self):
        from hf_sync.cli import _parse_destination

        r, p = _parse_destination("")
        assert r == ""
        assert p == ""


# ── _show_dry_run ─────────────────────────────────────────────────────


class TestShowDryRun:
    """_show_dry_run prints a table and warnings."""

    def test_accessible_repo(self):
        from hf_sync.cli import _show_dry_run
        from hf_sync.types.dto import DryRunReport

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
        from hf_sync.types.dto import DryRunReport

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


# ── auth ───────────────────────────────────────────────────────────────


class TestAuthCommand:
    """Auth command via CliRunner."""

    def test_auth_valid_token(self, cli_runner, tmp_path):
        from hf_sync.cli import app

        with (
            patch("huggingface_hub.HfApi.whoami") as mock_whoami,
            patch("hf_sync.database.Database.set_config") as mock_set,
        ):
            result = cli_runner.invoke(app, ["auth", "hf_test123"])
        assert result.exit_code == 0
        assert "Token validated and saved" in result.output
        mock_whoami.assert_called_once()
        mock_set.assert_awaited_once_with("hf_token", "hf_test123")

    def test_auth_invalid_token(self, cli_runner, tmp_path):
        from hf_sync.cli import app

        with (
            patch("huggingface_hub.HfApi.whoami", side_effect=Exception("Invalid token")),
            patch("hf_sync.database.Database.set_config"),
        ):
            result = cli_runner.invoke(app, ["auth", "hf_bad"])
        assert result.exit_code == 1
        assert "Token validation failed" in result.output

    def test_auth_warns_non_hf_token(self, cli_runner, tmp_path):
        from hf_sync.cli import app

        with (
            patch("huggingface_hub.HfApi.whoami"),
            patch("hf_sync.database.Database.set_config"),
        ):
            result = cli_runner.invoke(app, ["auth", "bad_token"])
        assert result.exit_code == 0
        assert "should start with hf_" in result.output


# ── config ──────────────────────────────────────────────────────────────


class TestConfigCommand:
    """Config command via CliRunner."""

    def test_config_sets_values(self, cli_runner):
        from hf_sync.cli import app
        from hf_sync.config import settings

        # Simulate user input for each prompt
        inputs = "my-repo\nhttp://custom:6800/jsonrpc\n\nmyremote\nmypath\n"
        with (
            patch("builtins.input", side_effect=inputs.split("\n")),
            patch("hf_sync.database.Database.set_config") as mock_set,
        ):
            result = cli_runner.invoke(app, ["config"])
        assert result.exit_code == 0
        assert "Configuration saved to DB" in result.output
        # Verify all non-empty inputs were saved
        assert mock_set.await_count == 4
        mock_set.assert_any_await("hf_repo_id", "my-repo")
        mock_set.assert_any_await("aria2_rpc_url", "http://custom:6800/jsonrpc")
        mock_set.assert_any_await("rclone_remote", "myremote")
        mock_set.assert_any_await("rclone_path", "mypath")
        # aria2_rpc_secret was left empty (Enter pressed) — not saved

    def test_config_skips_empty_input(self, cli_runner):
        from hf_sync.cli import app

        # All empty inputs (just press Enter for each)
        inputs = "\n\n\n\n\n"
        with (
            patch("builtins.input", side_effect=inputs.split("\n")),
            patch("hf_sync.database.Database.set_config") as mock_set,
        ):
            result = cli_runner.invoke(app, ["config"])
        assert result.exit_code == 0
        assert "Configuration saved to DB" in result.output
        mock_set.assert_not_awaited()


# ── doctor ─────────────────────────────────────────────────────────────


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
        """Cover line: if report.drive_error — adds hint to drive_status."""
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


# ── init ───────────────────────────────────────────────────────────────


class TestInitCommand:
    """Init command via CliRunner."""

    def test_init(self, cli_runner, tmp_path):
        from hf_sync.cli import app

        async def _fake_init(repo_id: str) -> None:
            return None

        with patch("hf_sync.cli.commands.init._init_impl", _fake_init):
            with patch("hf_sync.cli.commands.init.settings") as m_s:
                m_s.log_level = "WARNING"
                m_s.hf_token = "hf_test"
                result = cli_runner.invoke(app, ["init", "org/repo"])
        assert result.exit_code == 0


# ── start ──────────────────────────────────────────────────────────────


class TestStartCommand:
    """Start command via CliRunner."""

    def test_start_no_token(self, cli_runner):
        from hf_sync.cli import app

        with patch("hf_sync.cli.commands.start.settings") as m_s:
            m_s.log_level = "WARNING"
            m_s.hf_token = ""
            result = cli_runner.invoke(app, ["start", "org/repo", "gdrive:path"])
        assert result.exit_code == 1
        assert "HF_TOKEN not configured" in result.output

    def test_start_no_repo_id(self, cli_runner):
        from hf_sync.cli import app

        with patch("hf_sync.cli.commands.start.settings") as m_s:
            m_s.log_level = "WARNING"
            m_s.hf_token = "hf_test"
            m_s.hf_repo_id = ""
            result = cli_runner.invoke(app, ["start"])
        assert result.exit_code == 1
        assert "Specify a repo_id" in result.output

    def test_start_no_dest(self, cli_runner):
        from hf_sync.cli import app

        with patch("hf_sync.cli.commands.start.settings") as m_s:
            m_s.log_level = "WARNING"
            m_s.hf_token = "hf_test"
            m_s.hf_repo_id = "org/repo"
            m_s.rclone_remote = ""
            m_s.rclone_path = ""
            result = cli_runner.invoke(app, ["start"])
        assert result.exit_code == 1
        assert "Specify a destination" in result.output

    def test_start_dry_run(self, cli_runner):
        from hf_sync.cli import app

        with patch("hf_sync.cli.commands.start.settings") as m_s:
            m_s.log_level = "WARNING"
            m_s.hf_token = "hf_test"
            with patch("hf_sync.cli.commands.start._show_dry_run"):
                result = cli_runner.invoke(app, ["start", "org/repo", "gdrive:path", "--dry-run"])
        assert result.exit_code == 0

    def test_start_keyboard_interrupt(self, cli_runner):
        from hf_sync.cli import app

        with patch("hf_sync.cli.commands.start.settings") as m_s:
            m_s.log_level = "WARNING"
            m_s.hf_token = "hf_test"
            with patch("hf_sync.cli.commands.start._start_impl", side_effect=KeyboardInterrupt):
                result = cli_runner.invoke(app, ["start", "org/repo", "gdrive:path"])
        assert result.exit_code == 0
        assert "cancelled" in result.output.lower()

    def test_start_default_repo_and_dest(self, cli_runner):
        from hf_sync.cli import app

        with patch("hf_sync.cli.commands.start.settings") as m_s:
            m_s.log_level = "WARNING"
            m_s.hf_token = "hf_test"
            m_s.hf_repo_id = "org/repo"
            m_s.rclone_remote = "gdrive"
            m_s.rclone_path = "models"
            with patch("hf_sync.cli.commands.start._start_impl"):
                result = cli_runner.invoke(app, ["start"])
        assert result.exit_code == 0


# ── resume ─────────────────────────────────────────────────────────────


class TestResumeCommand:
    """Resume command via CliRunner."""

    def test_resume(self, cli_runner):
        from hf_sync.cli import app

        with patch("hf_sync.cli.commands.resume.settings") as m_s:
            m_s.log_level = "WARNING"
            with patch("hf_sync.cli.commands.resume._resume_impl") as m_impl:
                result = cli_runner.invoke(app, ["resume"])
        assert result.exit_code == 0
        m_impl.assert_called_once()


# ── verify ─────────────────────────────────────────────────────────────


class TestVerifyCommand:
    """Verify command via CliRunner."""

    def test_verify(self, cli_runner):
        from hf_sync.cli import app

        with patch("hf_sync.cli.commands.verify.settings") as m_s:
            m_s.log_level = "WARNING"
            with patch("hf_sync.cli.commands.verify._verify_impl") as m_impl:
                result = cli_runner.invoke(app, ["verify"])
        assert result.exit_code == 0
        m_impl.assert_called_once()


# ── _init_impl ─────────────────────────────────────────────────────────


class TestInitImpl:
    """Async _init_impl function."""

    @pytest.mark.asyncio
    async def test_init_with_files(self, tmp_path):
        from hf_sync.cli.commands.init import _init_impl

        conn = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_by_name = AsyncMock(return_value=None)

        mock_db_instance = MagicMock()
        mock_db_instance.connect = AsyncMock(return_value=conn)
        mock_db_cls = MagicMock()
        mock_db_cls.init_db = AsyncMock()
        mock_db_cls.return_value = mock_db_instance

        with patch("hf_sync.cli.commands.init.Database", mock_db_cls):
            with patch("hf_sync.cli.commands.init.FileRepository", return_value=mock_repo):
                with patch("hf_sync.cli.commands.init.HuggingFaceService") as m_hf:
                    with patch("hf_sync.cli.commands.init.Path") as m_path:
                        with patch("hf_sync.cli.commands.init.settings") as m_s:
                            m_s.temp_dir = str(tmp_path / "temp")
                            m_s.db_path = str(tmp_path / "state.db")
                            m_s.hf_token = "hf_test"
                            m_path.return_value.mkdir = MagicMock()

                            m_hf.return_value.list_files.return_value = [
                                {"filename": "f1.bin", "size": "100"},
                                {"filename": "f2.bin", "size": "200"},
                            ]

                            await _init_impl("org/repo")

        mock_db_cls.init_db.assert_awaited_once()
        assert mock_repo.insert.await_count == 2
        assert conn.close.await_count == 1

    @pytest.mark.asyncio
    async def test_init_no_token(self, tmp_path):
        from hf_sync.cli.commands.init import _init_impl

        mock_db_cls = MagicMock()
        mock_db_cls.init_db = AsyncMock()

        with patch("hf_sync.cli.commands.init.settings") as m_s:
            m_s.temp_dir = str(tmp_path / "temp")
            m_s.db_path = str(tmp_path / "state.db")
            m_s.hf_token = ""
            with patch("hf_sync.cli.commands.init.Database", mock_db_cls):
                await _init_impl("org/repo")

    @pytest.mark.asyncio
    async def test_init_no_repo_id(self, tmp_path):
        from hf_sync.cli.commands.init import _init_impl

        mock_db_cls = MagicMock()
        mock_db_cls.init_db = AsyncMock()

        with patch("hf_sync.cli.commands.init.settings") as m_s:
            m_s.temp_dir = str(tmp_path / "temp")
            m_s.db_path = str(tmp_path / "state.db")
            m_s.hf_token = "hf_test"
            with patch("hf_sync.cli.commands.init.Database", mock_db_cls):
                with patch("hf_sync.cli.commands.init.HuggingFaceService"):
                    await _init_impl("")

    @pytest.mark.asyncio
    async def test_init_repo_id_from_settings(self, tmp_path):
        from hf_sync.cli.commands.init import _init_impl

        conn = AsyncMock()
        mock_db_instance = MagicMock()
        mock_db_instance.connect = AsyncMock(return_value=conn)
        mock_db_cls = MagicMock()
        mock_db_cls.init_db = AsyncMock()
        mock_db_cls.return_value = mock_db_instance

        with patch("hf_sync.cli.commands.init.settings") as m_s:
            m_s.temp_dir = str(tmp_path / "temp")
            m_s.db_path = str(tmp_path / "state.db")
            m_s.hf_token = "hf_test"
            with patch("hf_sync.cli.commands.init.Database", mock_db_cls):
                with patch("hf_sync.cli.commands.init.FileRepository"):
                    with patch("hf_sync.cli.commands.init.HuggingFaceService") as m_hf:
                        m_hf.return_value.list_files.return_value = []
                        await _init_impl("org/repo")


# ── _start_impl ─────────────────────────────────────────────────────────────


class TestStartImpl:
    """Async _start_impl function."""

    @pytest.fixture(autouse=True)
    def cleanup_loguru(self):
        yield
        from loguru import logger as lg

        lg.remove()

    @pytest.mark.asyncio
    async def test_no_pending_files(self, tmp_path):
        """Exit early when no files are pending."""
        conn = AsyncMock()
        count_all = AsyncMock()
        count_all.fetchone.return_value = {"cnt": 3}
        count_pending = AsyncMock()
        count_pending.fetchone.return_value = {"cnt": 0}
        conn.execute.side_effect = [count_all, count_pending]
        conn.close = AsyncMock()

        mock_db = MagicMock()
        mock_db.connect = AsyncMock(return_value=conn)

        with patch("hf_sync.cli.commands.start.Database", return_value=mock_db):
            with patch("hf_sync.cli.commands.start.FileRepository") as m_repo:
                with patch("hf_sync.cli.commands.start.settings") as m_s:
                    m_s.temp_dir = str(tmp_path / "temp")
                    m_s.db_path = str(tmp_path / "state.db")
                    m_s.aria2_rpc_url = "http://localhost:6800/jsonrpc"
                    m_s.aria2_rpc_secret = ""
                    m_s.log_level = "WARNING"
                    m_s.hf_token = "hf_test"

                    from hf_sync.cli.commands.start import _start_impl

                    await _start_impl("org/repo", "gdrive", "path")

        assert conn.close.await_count == 1

    @pytest.mark.asyncio
    async def test_auto_init_then_sync(self, tmp_path):
        """Auto-init when DB empty, then sync files."""
        conn = AsyncMock()
        count_all = AsyncMock()
        count_all.fetchone.return_value = {"cnt": 0}
        count_pending = AsyncMock()
        count_pending.fetchone.return_value = {"cnt": 2}
        summary_cur = AsyncMock()
        summary_cur.fetchall.return_value = [{"status": "DONE", "cnt": 2}]
        conn.execute.side_effect = [count_all, count_pending, summary_cur]
        conn.commit = AsyncMock()
        conn.close = AsyncMock()

        mock_db = MagicMock()
        mock_db.connect = AsyncMock(return_value=conn)

        mock_repo = AsyncMock()
        mock_repo.get_pending.side_effect = [
            {"id": 1, "filename": "f1.bin", "local_path": "/tmp/f1.bin", "size": 100, "sha256": "abc"},
            {"id": 2, "filename": "f2.bin", "local_path": "/tmp/f2.bin", "size": 200, "sha256": "def"},
            None,
        ]
        mock_repo.insert = AsyncMock()
        mock_repo.get_by_name.return_value = None

        async def _run_with_cb(task, progress_callback=None):
            if progress_callback:
                progress_callback("download", 0, "")
                progress_callback("download", 50, "100MB/s")
                progress_callback("upload", 25, "")
            return (True, "")

        mock_coordinator = AsyncMock()
        mock_coordinator.run.side_effect = _run_with_cb

        mock_hf = MagicMock()
        mock_hf.list_files.return_value = [
            {"filename": "f1.bin", "size": "100"},
            {"filename": "f2.bin", "size": "200"},
        ]
        mock_hf.get_signed_url.return_value = "http://hf.co/f.bin"

        mock_live = MagicMock()

        with patch("hf_sync.cli.commands.start.Database", return_value=mock_db):
            with patch("hf_sync.cli.commands.start.FileRepository", return_value=mock_repo):
                with patch("hf_sync.cli.commands.start.HuggingFaceService", return_value=mock_hf):
                    with patch("hf_sync.cli.commands.start.Aria2Service"):
                        with patch("hf_sync.cli.commands.start.RcloneService"):
                            with patch("hf_sync.cli.commands.start.Coordinator", return_value=mock_coordinator):
                                with patch("rich.live.Live", return_value=mock_live):
                                    with patch("hf_sync.cli.commands.start.logger"):
                                        with patch("hf_sync.cli.commands.start.settings") as m_s:
                                            m_s.temp_dir = str(tmp_path / "temp")
                                            m_s.db_path = str(tmp_path / "state.db")
                                            m_s.aria2_rpc_url = "http://localhost:6800/jsonrpc"
                                            m_s.aria2_rpc_secret = ""
                                            m_s.log_level = "WARNING"
                                            m_s.hf_token = "hf_test"

                                            from hf_sync.cli.commands.start import _start_impl

                                            await _start_impl("org/repo", "gdrive", "path")

        assert mock_repo.get_pending.await_count == 3
        assert mock_repo.insert.await_count == 2
        assert mock_coordinator.run.await_count == 2
        assert conn.commit.await_count == 1

    @pytest.mark.asyncio
    async def test_sync_all_ok_no_auto_init(self, tmp_path):
        """Files already in DB, pending exist, all succeed."""
        conn = AsyncMock()
        count_all = AsyncMock()
        count_all.fetchone.return_value = {"cnt": 3}
        count_pending = AsyncMock()
        count_pending.fetchone.return_value = {"cnt": 2}
        summary_cur = AsyncMock()
        summary_cur.fetchall.return_value = [{"status": "DONE", "cnt": 2}]
        conn.execute.side_effect = [count_all, count_pending, summary_cur]
        conn.commit = AsyncMock()
        conn.close = AsyncMock()

        mock_db = MagicMock()
        mock_db.connect = AsyncMock(return_value=conn)

        mock_repo = AsyncMock()
        mock_repo.get_pending.side_effect = [
            {"id": 1, "filename": "f1.bin", "local_path": "/tmp/f1.bin", "size": 100, "sha256": "abc"},
            {"id": 2, "filename": "f2.bin", "local_path": "/tmp/f2.bin", "size": 200, "sha256": "def"},
            None,
        ]

        mock_coordinator = AsyncMock()
        mock_coordinator.run.return_value = (True, "")

        mock_hf = MagicMock()
        mock_hf.get_signed_url.return_value = "http://hf.co/f.bin"

        mock_live = MagicMock()

        with patch("hf_sync.cli.commands.start.Database", return_value=mock_db):
            with patch("hf_sync.cli.commands.start.FileRepository", return_value=mock_repo):
                with patch("hf_sync.cli.commands.start.HuggingFaceService", return_value=mock_hf):
                    with patch("hf_sync.cli.commands.start.Aria2Service"):
                        with patch("hf_sync.cli.commands.start.RcloneService"):
                            with patch("hf_sync.cli.commands.start.Coordinator", return_value=mock_coordinator):
                                with patch("rich.live.Live", return_value=mock_live):
                                    with patch("hf_sync.cli.commands.start.logger"):
                                        with patch("hf_sync.cli.commands.start.settings") as m_s:
                                            m_s.temp_dir = str(tmp_path / "temp")
                                            m_s.db_path = str(tmp_path / "state.db")
                                            m_s.aria2_rpc_url = "http://localhost:6800/jsonrpc"
                                            m_s.aria2_rpc_secret = ""
                                            m_s.log_level = "WARNING"
                                            m_s.hf_token = "hf_test"

                                            from hf_sync.cli.commands.start import _start_impl

                                            await _start_impl("org/repo", "gdrive", "path")

        assert mock_coordinator.run.await_count == 2
        assert conn.commit.await_count == 1

    @pytest.mark.asyncio
    async def test_sync_some_fail(self, tmp_path):
        """Some files fail, completed_lines track errors."""
        conn = AsyncMock()
        count_all = AsyncMock()
        count_all.fetchone.return_value = {"cnt": 3}
        count_pending = AsyncMock()
        count_pending.fetchone.return_value = {"cnt": 2}
        summary_cur = AsyncMock()
        summary_cur.fetchall.return_value = [{"status": "DONE", "cnt": 1}, {"status": "FAILED", "cnt": 1}]
        conn.execute.side_effect = [count_all, count_pending, summary_cur]
        conn.commit = AsyncMock()
        conn.close = AsyncMock()

        mock_db = MagicMock()
        mock_db.connect = AsyncMock(return_value=conn)

        mock_repo = AsyncMock()
        mock_repo.get_pending.side_effect = [
            {"id": 1, "filename": "f1.bin", "local_path": "/tmp/f1.bin", "size": 100, "sha256": "abc"},
            {"id": 2, "filename": "f2.bin", "local_path": "/tmp/f2.bin", "size": 200, "sha256": "def"},
            None,
        ]

        mock_coordinator = AsyncMock()
        mock_coordinator.run.side_effect = [(True, ""), (False, "upload error")]

        mock_hf = MagicMock()
        mock_hf.get_signed_url.return_value = "http://hf.co/f.bin"

        mock_live = MagicMock()

        with patch("hf_sync.cli.commands.start.Database", return_value=mock_db):
            with patch("hf_sync.cli.commands.start.FileRepository", return_value=mock_repo):
                with patch("hf_sync.cli.commands.start.HuggingFaceService", return_value=mock_hf):
                    with patch("hf_sync.cli.commands.start.Aria2Service"):
                        with patch("hf_sync.cli.commands.start.RcloneService"):
                            with patch("hf_sync.cli.commands.start.Coordinator", return_value=mock_coordinator):
                                with patch("rich.live.Live", return_value=mock_live):
                                    with patch("hf_sync.cli.commands.start.logger"):
                                        with patch("hf_sync.cli.commands.start.settings") as m_s:
                                            m_s.temp_dir = str(tmp_path / "temp")
                                            m_s.db_path = str(tmp_path / "state.db")
                                            m_s.aria2_rpc_url = "http://localhost:6800/jsonrpc"
                                            m_s.aria2_rpc_secret = ""
                                            m_s.log_level = "WARNING"
                                            m_s.hf_token = "hf_test"

                                            from hf_sync.cli.commands.start import _start_impl

                                            await _start_impl("org/repo", "gdrive", "path")

        assert mock_coordinator.run.await_count == 2
        assert conn.commit.await_count == 1

    @pytest.mark.asyncio
    async def test_sync_many_files_cover_all_lines(self, tmp_path):
        """>10 files trigger completed_lines pop; PENDING in summary."""
        conn = AsyncMock()
        count_all = AsyncMock()
        count_all.fetchone.return_value = {"cnt": 12}
        count_pending = AsyncMock()
        count_pending.fetchone.return_value = {"cnt": 12}
        summary_cur = AsyncMock()
        summary_cur.fetchall.return_value = [
            {"status": "DONE", "cnt": 12},
            {"status": "PENDING", "cnt": 0},
        ]
        conn.execute.side_effect = [count_all, count_pending, summary_cur]
        conn.commit = AsyncMock()
        conn.close = AsyncMock()

        mock_db = MagicMock()
        mock_db.connect = AsyncMock(return_value=conn)

        pending_files: list[dict[str, int | str] | None] = [
            {"id": i, "filename": f"f{i}.bin", "local_path": f"/tmp/f{i}.bin", "size": 100 * i, "sha256": f"abc{i}"}
            for i in range(1, 13)
        ]
        pending_files.append(None)
        mock_repo = AsyncMock()
        mock_repo.get_pending.side_effect = pending_files

        mock_coordinator = AsyncMock()
        mock_coordinator.run.return_value = (True, "")

        mock_hf = MagicMock()
        mock_hf.get_signed_url.return_value = "http://hf.co/f.bin"

        mock_live = MagicMock()

        with patch("hf_sync.cli.commands.start.Database", return_value=mock_db):
            with patch("hf_sync.cli.commands.start.FileRepository", return_value=mock_repo):
                with patch("hf_sync.cli.commands.start.HuggingFaceService", return_value=mock_hf):
                    with patch("hf_sync.cli.commands.start.Aria2Service"):
                        with patch("hf_sync.cli.commands.start.RcloneService"):
                            with patch("hf_sync.cli.commands.start.Coordinator", return_value=mock_coordinator):
                                with patch("rich.live.Live", return_value=mock_live):
                                    with patch("hf_sync.cli.commands.start.logger"):
                                        with patch("hf_sync.cli.commands.start.settings") as m_s:
                                            m_s.temp_dir = str(tmp_path / "temp")
                                            m_s.db_path = str(tmp_path / "state.db")
                                            m_s.aria2_rpc_url = "http://localhost:6800/jsonrpc"
                                            m_s.aria2_rpc_secret = ""
                                            m_s.log_level = "WARNING"
                                            m_s.hf_token = "hf_test"

                                            from hf_sync.cli.commands.start import _start_impl

                                            await _start_impl("org/repo", "gdrive", "path")

        assert mock_coordinator.run.await_count == 12
        assert conn.commit.await_count == 1


# ── _resume_impl ───────────────────────────────────────────────────────


class TestResumeImpl:
    """Async _resume_impl function."""

    @pytest.mark.asyncio
    async def test_reset_failed_files(self, tmp_path):
        conn = AsyncMock()
        cur = AsyncMock()
        cur.fetchall.return_value = [
            {"id": 1, "local_path": str(tmp_path / "f1.bin")},
            {"id": 2, "local_path": str(tmp_path / "nonexistent.bin")},
        ]
        conn.execute.return_value = cur
        conn.commit = AsyncMock()
        conn.close = AsyncMock()

        # Create temp file to test unlink
        tmp_file = tmp_path / "f1.bin"
        tmp_file.write_text("dummy")

        mock_db = MagicMock()
        mock_db.connect = AsyncMock(return_value=conn)

        with patch("hf_sync.cli.commands.resume.Database", return_value=mock_db):
            with patch("hf_sync.cli.commands.resume.settings") as m_s:
                m_s.log_level = "WARNING"
                m_s.db_path = str(tmp_path / "state.db")

                from hf_sync.cli.commands.resume import _resume_impl

                await _resume_impl()

        assert not tmp_file.exists()
        assert conn.execute.await_count >= 2  # SELECT + UPDATE
        assert conn.commit.await_count == 1
        assert conn.close.await_count == 1

    @pytest.mark.asyncio
    async def test_reset_no_failed_files(self, tmp_path):
        conn = AsyncMock()
        cur = AsyncMock()
        cur.fetchall.return_value = []
        conn.execute.return_value = cur
        conn.commit = AsyncMock()
        conn.close = AsyncMock()

        mock_db = MagicMock()
        mock_db.connect = AsyncMock(return_value=conn)

        with patch("hf_sync.cli.commands.resume.Database", return_value=mock_db):
            with patch("hf_sync.cli.commands.resume.settings") as m_s:
                m_s.log_level = "WARNING"
                m_s.db_path = str(tmp_path / "state.db")

                from hf_sync.cli.commands.resume import _resume_impl

                await _resume_impl()

        assert conn.close.await_count == 1


# ── _verify_impl ───────────────────────────────────────────────────────


class TestVerifyImpl:
    """Async _verify_impl function."""

    @pytest.mark.asyncio
    async def test_verify_all_ok(self, tmp_path):
        conn = AsyncMock()
        cur = AsyncMock()
        cur.fetchall.return_value = [
            {"id": 1, "filename": "ok.bin", "local_path": "/tmp/ok.bin", "size": 100, "sha256": "abc", "status": "DONE"},
            {"id": 2, "filename": "ok2.bin", "local_path": "/tmp/ok2.bin", "size": 200, "sha256": "def", "status": "DONE"},
        ]
        conn.execute.return_value = cur
        conn.close = AsyncMock()

        mock_db = MagicMock()
        mock_db.connect = AsyncMock(return_value=conn)

        with patch("hf_sync.cli.commands.verify.Database", return_value=mock_db):
            with patch("hf_sync.cli.commands.verify.Verifier") as m_ver:
                m_ver.return_value.verify.return_value = True
                with patch("hf_sync.cli.commands.verify.settings") as m_s:
                    m_s.log_level = "WARNING"
                    m_s.db_path = str(tmp_path / "state.db")

                    from hf_sync.cli.commands.verify import _verify_impl

                    await _verify_impl()

        assert conn.close.await_count == 1

    @pytest.mark.asyncio
    async def test_verify_some_fail(self, tmp_path):
        conn = AsyncMock()
        cur = AsyncMock()
        cur.fetchall.return_value = [
            {"id": 1, "filename": "ok.bin", "local_path": "/tmp/ok.bin", "size": 100, "sha256": "abc", "status": "DONE"},
            {"id": 2, "filename": "bad.bin", "local_path": "/tmp/bad.bin", "size": 200, "sha256": "xyz", "status": "DONE"},
        ]
        conn.execute.return_value = cur
        conn.close = AsyncMock()

        mock_db = MagicMock()
        mock_db.connect = AsyncMock(return_value=conn)

        with patch("hf_sync.cli.commands.verify.Database", return_value=mock_db):
            with patch("hf_sync.cli.commands.verify.Verifier") as m_ver:
                m_ver.return_value.verify.side_effect = [True, False]
                with patch("hf_sync.cli.commands.verify.settings") as m_s:
                    m_s.log_level = "WARNING"
                    m_s.db_path = str(tmp_path / "state.db")

                    from hf_sync.cli.commands.verify import _verify_impl

                    await _verify_impl()

        assert m_ver.return_value.verify.call_count == 2
        assert conn.close.await_count == 1

# ── update ──────────────────────────────────────────────────────────────


class TestUpdateCommand:
    """Update command via CliRunner."""

    def test_update_already_up_to_date(self, cli_runner):
        from hf_sync.cli import app

        with (
            patch("hf_sync.cli.commands.update.pkg_version", return_value="0.1.0"),
            patch("httpx.get") as mock_get,
        ):
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"tag_name": "v0.1.0"}
            result = cli_runner.invoke(app, ["update"])
        assert result.exit_code == 0
        assert "Current version: 0.1.0" in result.output
        assert "Latest version:  0.1.0" in result.output
        assert "Already up to date" in result.output

    def test_update_new_version_available(self, cli_runner):
        from hf_sync.cli import app

        with (
            patch("hf_sync.cli.commands.update.pkg_version", return_value="0.1.0"),
            patch("httpx.get") as mock_get,
            patch("subprocess.run") as mock_run,
        ):
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"tag_name": "v0.2.0"}
            mock_run.return_value = MagicMock()
            result = cli_runner.invoke(app, ["update"])
        assert result.exit_code == 0
        assert "Updated to 0.2.0" in result.output
        mock_run.assert_called_once_with(
            ["uv", "tool", "install", "--from", "https://github.com/bryxnsal/hf-sync.git", "hf-sync", "--upgrade"],
            check=True,
            capture_output=False,
        )

    def test_update_new_version_fallback_pip(self, cli_runner):
        from hf_sync.cli import app

        with (
            patch("hf_sync.cli.commands.update.pkg_version", return_value="0.1.0"),
            patch("httpx.get") as mock_get,
            patch("subprocess.run") as mock_run,
            patch.object(sys, "executable", "/usr/bin/python3"),
        ):
            # uv not found → fallback to pip
            mock_run.side_effect = [FileNotFoundError(), MagicMock()]
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"tag_name": "v0.2.0"}
            result = cli_runner.invoke(app, ["update"])
        assert result.exit_code == 0
        assert "Updated to 0.2.0" in result.output
        # First call fails (FileNotFoundError), second call is pip
        assert mock_run.call_count == 2
        assert mock_run.call_args.args[0] == ["/usr/bin/python3", "-m", "pip", "install", "--upgrade",
            f"git+https://github.com/bryxnsal/hf-sync.git"]


    def test_update_dev_build_ahead(self, cli_runner):
        from hf_sync.cli import app

        with (
            patch("hf_sync.cli.commands.update.pkg_version", return_value="0.4.1.dev1+g1a41c28d2"),
            patch("httpx.get") as mock_get,
        ):
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"tag_name": "v0.4.0"}
            result = cli_runner.invoke(app, ["update"])
        assert result.exit_code == 0
        assert "Dev build" in result.output
        assert "ahead of latest release" in result.output
    def test_update_api_failure(self, cli_runner):
        from hf_sync.cli import app

        with (
            patch("hf_sync.cli.commands.update.pkg_version", return_value="0.1.0"),
            patch("httpx.get", side_effect=Exception("Network error")),
        ):
            result = cli_runner.invoke(app, ["update"])
        assert result.exit_code == 1
        assert "Failed to check latest version" in result.output

    def test_update_uv_install_fails(self, cli_runner):
        from hf_sync.cli import app

        with (
            patch("hf_sync.cli.commands.update.pkg_version", return_value="0.1.0"),
            patch("httpx.get") as mock_get,
            patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, ["uv"])),
        ):
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"tag_name": "v0.2.0"}
            result = cli_runner.invoke(app, ["update"])
        assert result.exit_code == 1
        assert "uv upgrade failed" in result.output

    def test_update_pip_upgrade_fails(self, cli_runner):
        from hf_sync.cli import app

        with (
            patch("hf_sync.cli.commands.update.pkg_version", return_value="0.1.0"),
            patch("httpx.get") as mock_get,
            patch("subprocess.run") as mock_run,
            patch.object(sys, "executable", "/usr/bin/python3"),
        ):
            mock_run.side_effect = [
                FileNotFoundError(),
                subprocess.CalledProcessError(1, ["pip"]),
            ]
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"tag_name": "v0.2.0"}
            result = cli_runner.invoke(app, ["update"])
        assert result.exit_code == 1
        assert "pip upgrade failed" in result.output


# ── main ───────────────────────────────────────────────────────────────


class TestMain:
    """main entry point."""

    def test_main_app_reference(self):
        from hf_sync.cli import main, app

        assert main is not None
        assert app is not None

    def test_version_flag(self, cli_runner):
        from hf_sync.cli import app

        result = cli_runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "hf-sync v" in result.output

    def test_version_short_flag(self, cli_runner):
        from hf_sync.cli import app

        result = cli_runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert "hf-sync v" in result.output

    def test_version_fallback(self, cli_runner):
        from hf_sync.cli import app

        with patch("importlib.metadata.version", side_effect=Exception("not found")):
            result = cli_runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "hf-sync v0.0.0" in result.output

    def test_no_command_shows_help(self, cli_runner):
        from hf_sync.cli import app

        result = cli_runner.invoke(app, [])
        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "Commands" in result.output
        assert "--version" in result.output

    def test_version_flag_before_command(self, cli_runner):
        from hf_sync.cli import app

        # --version before any command should exit directly without running command
        result = cli_runner.invoke(app, ["--version", "doctor"])
        assert result.exit_code == 0
        assert "hf-sync v" in result.output
