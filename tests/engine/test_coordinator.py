"""Tests for Coordinator — orchestrates download → upload → verify → cleanup."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call

import pytest

from hf_sync.engine.coordinator import Coordinator
from hf_sync.types.dto import SyncTask


@pytest.fixture
def task():
    return SyncTask(
        file_id=42,
        filename="test.bin",
        source_url="http://hf.co/test.bin",
        local_path="/tmp/test.bin",
        remote_path="gdrive:models/test.bin",
        size=1000,
        sha256="abc123",
    )


@pytest.fixture
def coordinator():
    downloader = MagicMock()
    downloader.download.return_value = "gid123"
    downloader.wait_for_completion.return_value = {"status": "complete"}

    uploader = MagicMock()
    uploader.upload = AsyncMock()

    verifier = MagicMock()
    verifier.verify.return_value = True

    cleanup = MagicMock()

    repo = MagicMock()
    repo.update_status = AsyncMock()
    repo.mark_done = AsyncMock()
    repo.mark_failed = AsyncMock()
    repo.add_event = AsyncMock()

    return Coordinator(
        downloader=downloader,
        uploader=uploader,
        verifier=verifier,
        cleanup=cleanup,
        repo=repo,
        temp_dir="/tmp",
    )


@pytest.mark.asyncio
async def test_full_pipeline_success(coordinator, task):
    """Download → upload → verify → cleanup → mark_done."""
    success, msg = await coordinator.run(task)
    assert success
    assert msg == ""

    coordinator.repo.update_status.assert_has_awaits([
        call(task.file_id, "DOWNLOADING"),
        call(task.file_id, "UPLOADING"),
        call(task.file_id, "VERIFYING"),
    ])
    coordinator.repo.mark_done.assert_awaited_once_with(task.file_id)
    coordinator.downloader.download.assert_called_once_with(task.source_url, task.local_path)
    coordinator.uploader.upload.assert_awaited_once()
    coordinator.verifier.verify.assert_called_once_with(task.local_path, task.size, task.sha256)
    coordinator.cleanup.remove_local.assert_called_once_with(task.local_path)


@pytest.mark.asyncio
async def test_download_failure(coordinator, task):
    coordinator.downloader.wait_for_completion.return_value = {"status": "error"}
    success, msg = await coordinator.run(task)
    assert not success
    coordinator.repo.mark_failed.assert_awaited_once_with(task.file_id)
    coordinator.cleanup.remove_local.assert_called_once_with(task.local_path)


@pytest.mark.asyncio
async def test_download_raises_exception(coordinator, task):
    coordinator.downloader.download.side_effect = RuntimeError("no aria2")
    success, msg = await coordinator.run(task)
    assert not success
    assert "no aria2" in msg


@pytest.mark.asyncio
async def test_upload_failure(coordinator, task):
    coordinator.uploader.upload.side_effect = RuntimeError("upload failed")
    success, msg = await coordinator.run(task)
    assert not success
    assert "upload failed" in msg
    coordinator.repo.mark_failed.assert_awaited_once_with(task.file_id)
    coordinator.cleanup.remove_local.assert_called_once_with(task.local_path)


@pytest.mark.asyncio
async def test_verify_failure(coordinator, task):
    coordinator.verifier.verify.return_value = False
    success, msg = await coordinator.run(task)
    assert not success
    assert "Verification failed" in msg
    coordinator.repo.mark_failed.assert_awaited_once_with(task.file_id)
    coordinator.cleanup.remove_local.assert_called_once_with(task.local_path)


@pytest.mark.asyncio
async def test_events_recorded_for_success(coordinator, task):
    await coordinator.run(task)
    events = [c.args for c in coordinator.repo.add_event.await_args_list]
    # Should have: download_start, download_done, upload_start, upload_done,
    #              verify_start, verify_done, cleanup_done
    event_types = [e[1] for e in events]
    assert "download_start" in event_types
    assert "download_done" in event_types
    assert "upload_start" in event_types
    assert "upload_done" in event_types
    assert "verify_start" in event_types
    assert "verify_done" in event_types
    assert "cleanup_done" in event_types


@pytest.mark.asyncio
async def test_events_recorded_for_download_failure(coordinator, task):
    coordinator.downloader.wait_for_completion.return_value = {"status": "error"}
    await coordinator.run(task)
    events = [c.args[1] for c in coordinator.repo.add_event.await_args_list]
    assert "download_start" in events
    assert "download_fail" in events
    assert "upload_start" not in events


@pytest.mark.asyncio
async def test_progress_callback_called(coordinator, task):
    cb = MagicMock()
    await coordinator.run(task, progress_callback=cb)
    assert cb.call_count >= 3  # download 0%, upload 0%, verify 0%


@pytest.mark.asyncio
async def test_dl_progress_callback_with_speed(coordinator, task):
    """_dl_progress coverage: wait_for_completion passes speed to progress_callback."""
    cb = MagicMock()
    # Make wait_for_completion invoke its progress_callback with real values
    def _mock_wait(gid: str, progress_callback=None):
        if progress_callback:
            progress_callback(500, 1000, 102400)  # completed, total, speed bytes/s
        return {"status": "complete"}
    coordinator.downloader.wait_for_completion.side_effect = _mock_wait
    await coordinator.run(task, progress_callback=cb)
    # cb should have been called with "download", 50.0, "100.0KB/s"
    cb.assert_any_call("download", 50.0, "100.0KB/s")


@pytest.mark.asyncio
async def test_no_remote_path_defaults_to_filename(coordinator):
    t = SyncTask(
        file_id=1,
        filename="f.bin",
        source_url="http://hf.co/f.bin",
        local_path="/tmp/f.bin",
        remote_path="",
    )
    await coordinator.run(t)
    uploaded_path = coordinator.uploader.upload.call_args[0][1]
    assert uploaded_path == "f.bin"


@pytest.mark.asyncio
async def test_cleanup_not_called_on_verify_failure(coordinator, task):
    """Temp file should be cleaned up on verify failure too (to free space)."""
    coordinator.verifier.verify.return_value = False
    await coordinator.run(task)
    coordinator.cleanup.remove_local.assert_called_once_with(task.local_path)
