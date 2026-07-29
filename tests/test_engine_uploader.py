"""Tests for Uploader — wraps RcloneService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from hf_sync.engine.uploader import Uploader


@pytest.fixture
def mock_rclone():
    svc = MagicMock()
    svc.copyto_async = AsyncMock()
    return svc


@pytest.fixture
def uploader(mock_rclone):
    return Uploader(mock_rclone)


@pytest.mark.asyncio
async def test_upload_calls_copyto_async(uploader, mock_rclone):
    await uploader.upload("/tmp/f.bin", "remote:path/f.bin")
    mock_rclone.copyto_async.assert_called_once_with(
        "/tmp/f.bin", "remote:path/f.bin", progress_callback=None
    )


@pytest.mark.asyncio
async def test_upload_forwards_progress_callback(uploader, mock_rclone):
    cb = MagicMock()
    await uploader.upload("/tmp/f.bin", "remote:path/f.bin", progress_callback=cb)
    mock_rclone.copyto_async.assert_called_once_with(
        "/tmp/f.bin", "remote:path/f.bin", progress_callback=cb
    )


@pytest.mark.asyncio
async def test_upload_passes_rclone_error(uploader, mock_rclone):
    mock_rclone.copyto_async.side_effect = RuntimeError("rclone failed")
    with pytest.raises(RuntimeError, match="rclone failed"):
        await uploader.upload("/tmp/f.bin", "remote:path/f.bin")


@pytest.mark.asyncio
async def test_upload_connection_error_propagates(uploader, mock_rclone):
    mock_rclone.copyto_async.side_effect = ConnectionError("no route to host")
    with pytest.raises(ConnectionError):
        await uploader.upload("/tmp/f.bin", "remote:path/f.bin")
