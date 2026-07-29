"""Tests for CLI start command."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    return CliRunner()


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
