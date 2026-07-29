"""Tests for CLI init command."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    return CliRunner()


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
