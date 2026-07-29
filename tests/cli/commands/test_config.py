"""Tests for CLI config command."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestConfigCommand:
    """Config command via CliRunner."""

    def test_config_sets_values(self, cli_runner):
        from hf_sync.cli import app

        inputs = "my-repo\nhttp://custom:6800/jsonrpc\n\nmyremote\nmypath\n"
        with (
            patch("builtins.input", side_effect=inputs.split("\n")),
            patch("hf_sync.database.Database.set_config") as mock_set,
        ):
            result = cli_runner.invoke(app, ["config"])
        assert result.exit_code == 0
        assert "Configuration saved to DB" in result.output
        assert mock_set.await_count == 4
        mock_set.assert_any_await("hf_repo_id", "my-repo")
        mock_set.assert_any_await("aria2_rpc_url", "http://custom:6800/jsonrpc")
        mock_set.assert_any_await("rclone_remote", "myremote")
        mock_set.assert_any_await("rclone_path", "mypath")

    def test_config_skips_empty_input(self, cli_runner):
        from hf_sync.cli import app

        inputs = "\n\n\n\n\n"
        with (
            patch("builtins.input", side_effect=inputs.split("\n")),
            patch("hf_sync.database.Database.set_config") as mock_set,
        ):
            result = cli_runner.invoke(app, ["config"])
        assert result.exit_code == 0
        assert "Configuration saved to DB" in result.output
        mock_set.assert_not_awaited()
