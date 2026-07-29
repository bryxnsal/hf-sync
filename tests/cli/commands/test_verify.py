"""Tests for CLI verify command."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    return CliRunner()


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
