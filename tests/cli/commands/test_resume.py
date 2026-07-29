"""Tests for CLI resume command."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    return CliRunner()


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
        assert conn.execute.await_count >= 2
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
