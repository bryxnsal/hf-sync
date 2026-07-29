"""Tests for CLI update command."""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestUpdateCommand:
    """Update command via CliRunner."""

    _GIT_REPO: str = "https://github.com/bryxnsal/hf-sync.git"

    def _mock_api_resp(self, tag: str) -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"tag_name": tag, "assets": []}
        return resp

    def test_update_already_up_to_date(self, cli_runner):
        from hf_sync.cli import app

        with (
            patch("hf_sync.cli.commands.update.pkg_version", return_value="0.1.0"),
            patch("httpx.get") as mock_get,
        ):
            mock_get.return_value = self._mock_api_resp("v0.1.0")
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
            mock_get.return_value = self._mock_api_resp("v0.2.0")
            mock_run.return_value = MagicMock()
            result = cli_runner.invoke(app, ["update"])
        assert result.exit_code == 0
        assert "Updated to 0.2.0" in result.output
        mock_run.assert_called_once_with(
            ["uv", "tool", "install", "--from", f"{self._GIT_REPO}@v0.2.0", "hf-sync", "--upgrade"],
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
            mock_get.return_value = self._mock_api_resp("v0.2.0")
            mock_run.side_effect = [FileNotFoundError(), MagicMock()]
            result = cli_runner.invoke(app, ["update"])
        assert result.exit_code == 0
        assert "Updated to 0.2.0" in result.output
        assert mock_run.call_count == 2
        assert mock_run.call_args.args[0] == [
            "/usr/bin/python3", "-m", "pip", "install", "--upgrade",
            f"git+https://github.com/bryxnsal/hf-sync.git@v0.2.0",
        ]

    def test_update_dev_build_installs_stable(self, cli_runner):
        from hf_sync.cli import app

        with (
            patch("hf_sync.cli.commands.update.pkg_version", return_value="0.4.1.dev1+g1a41c28d2"),
            patch("httpx.get") as mock_get,
            patch("subprocess.run") as mock_run,
        ):
            mock_get.return_value = self._mock_api_resp("v0.4.0")
            mock_run.return_value = MagicMock()
            result = cli_runner.invoke(app, ["update"])
        assert result.exit_code == 0
        assert "Dev build" in result.output
        assert "installing stable" in result.output
        assert "Updated to 0.4.0" in result.output

    def test_update_dev_build_same_release(self, cli_runner):
        """Dev build for same release version = already have it."""
        from hf_sync.cli import app

        with (
            patch("hf_sync.cli.commands.update.pkg_version", return_value="0.4.0.dev2+deadbeef"),
            patch("httpx.get") as mock_get,
        ):
            mock_get.return_value = self._mock_api_resp("v0.4.0")
            result = cli_runner.invoke(app, ["update"])
        assert result.exit_code == 0
        assert "Already at 0.4.0" in result.output

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
            mock_get.return_value = self._mock_api_resp("v0.2.0")
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
            mock_get.return_value = self._mock_api_resp("v0.2.0")
            mock_run.side_effect = [
                FileNotFoundError(),
                subprocess.CalledProcessError(1, ["pip"]),
            ]
            result = cli_runner.invoke(app, ["update"])
        assert result.exit_code == 1
        assert "pip upgrade failed" in result.output
