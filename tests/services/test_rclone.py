"""Tests for RcloneService — subprocess wrapper."""

from __future__ import annotations

import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hf_sync.services.rclone import RcloneService


@pytest.fixture
def svc():
    return RcloneService(remote="gdrive")


class TestInit:
    def test_remote(self, svc: RcloneService):
        assert svc.remote == "gdrive"

    def test_default_remote(self):
        svc = RcloneService()
        assert svc.remote == ""


class TestSyncMethods:
    def test_copyto_success(self, svc: RcloneService):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], returncode=0, stdout="", stderr=""
            )
            svc.copyto("/tmp/f.bin", "gdrive:path/f.bin")
            mock_run.assert_called_once_with(
                ["rclone", "copyto", "/tmp/f.bin", "gdrive:path/f.bin"],
                capture_output=True, text=True,
            )

    def test_copyto_failure(self, svc: RcloneService):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], returncode=1, stdout="", stderr="error: no space",
            )
            with pytest.raises(RuntimeError, match="no space"):
                svc.copyto("/tmp/f.bin", "gdrive:path/f.bin")

    def test_lsjson_success(self, svc: RcloneService):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], returncode=0, stdout='[{"Name":"f.bin","Size":100}]', stderr="",
            )
            result = svc.lsjson("gdrive:path")
            assert len(result) == 1
            assert result[0]["Name"] == "f.bin"

    def test_lsjson_failure_returns_empty(self, svc: RcloneService):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], returncode=1, stdout="", stderr="error",
            )
            assert svc.lsjson("gdrive:path") == []

    def test_lsjson_empty_stdout(self, svc: RcloneService):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], returncode=0, stdout="", stderr="",
            )
            assert svc.lsjson("gdrive:path") == []

    def test_delete(self, svc: RcloneService):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], returncode=0, stdout="", stderr=""
            )
            svc.delete("gdrive:path/f.bin")
            mock_run.assert_called_once_with(
                ["rclone", "deletefile", "gdrive:path/f.bin"],
                capture_output=True, text=True,
            )

    def test_exists_true(self, svc: RcloneService):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], returncode=0, stdout='[{"Name":"f.bin"}]', stderr="",
            )
            assert svc.exists("gdrive:path/f.bin") is True

    def test_exists_false(self, svc: RcloneService):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], returncode=1, stdout="", stderr="",
            )
            assert svc.exists("gdrive:path/f.bin") is False

    def test_free_space(self, svc: RcloneService):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], returncode=0, stdout='{"free": 10737418240}', stderr="",
            )
            space = svc.free_space("gdrive:")
            assert space == 10.0

    def test_free_space_failure(self, svc: RcloneService):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], returncode=1, stdout="", stderr="error",
            )
            assert svc.free_space("gdrive:") == 0.0


class TestAsyncCopyto:
    @pytest.mark.asyncio
    async def test_with_progress_callback(self):
        svc = RcloneService(remote="gdrive")
        mock_process = AsyncMock()
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_stderr = AsyncMock()
        mock_stderr.readline.side_effect = [
            b"Transferred:   50% / 100MB, 10MB/s, ETA 5s\n",
            b"",
        ]
        mock_process.stderr = mock_stderr

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            cb = MagicMock()
            await svc.copyto_async("/tmp/f.bin", "gdrive:path/f.bin", progress_callback=cb)
            cb.assert_called_once_with("upload", 50.0, "10MB/s")

    @pytest.mark.asyncio
    async def test_without_callback_falls_back_to_sync(self):
        svc = RcloneService(remote="gdrive")
        with patch.object(svc, "copyto") as mock_copyto:
            await svc.copyto_async("/tmp/f.bin", "gdrive:path/f.bin")
            mock_copyto.assert_called_once_with("/tmp/f.bin", "gdrive:path/f.bin")

    @pytest.mark.asyncio
    async def test_progress_without_speed(self):
        svc = RcloneService(remote="gdrive")
        mock_process = AsyncMock()
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_stderr = AsyncMock()
        mock_stderr.readline.side_effect = [
            b"Transferred:   75%\n",
            b"",
        ]
        mock_process.stderr = mock_stderr

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            cb = MagicMock()
            await svc.copyto_async("/tmp/f.bin", "gdrive:path/f.bin", progress_callback=cb)
            cb.assert_called_once_with("upload", 75.0, "")

    @pytest.mark.asyncio
    async def test_failure_raises(self):
        svc = RcloneService(remote="gdrive")
        mock_process = AsyncMock()
        mock_process.wait.return_value = 1
        mock_process.returncode = 1
        mock_stderr = AsyncMock()
        mock_stderr.readline.side_effect = [b"", b""]
        mock_process.stderr = mock_stderr

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            cb = MagicMock()
            with pytest.raises(RuntimeError, match="rclone copyto failed"):
                await svc.copyto_async("/tmp/f.bin", "gdrive:path/f.bin", progress_callback=cb)

    @pytest.mark.asyncio
    async def test_multiple_progress_lines(self):
        svc = RcloneService(remote="gdrive")
        mock_process = AsyncMock()
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_stderr = AsyncMock()
        mock_stderr.readline.side_effect = [
            b"Transferred:   25% / 100MB, 5MB/s\n",
            b"Transferred:   75% / 100MB, 8MB/s\n",
            b"",
        ]
        mock_process.stderr = mock_stderr

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            cb = MagicMock()
            await svc.copyto_async("/tmp/f.bin", "gdrive:path/f.bin", progress_callback=cb)
            assert cb.call_count == 2
