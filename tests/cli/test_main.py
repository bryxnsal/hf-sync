"""Tests for CLI main entry point."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestMain:
    """main entry point."""

    def test_main_app_reference(self):
        from hf_sync.cli import app, main

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

        result = cli_runner.invoke(app, ["--version", "doctor"])
        assert result.exit_code == 0
        assert "hf-sync v" in result.output
