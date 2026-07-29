"""Tests for CLI auth command."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    return CliRunner()


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
