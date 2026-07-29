"""Tests for Scheduler — feeds pending files to Coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from hf_sync.scheduler import Scheduler


@pytest.fixture
def scheduler():
    coordinator = MagicMock()
    coordinator.run = AsyncMock()
    repo = MagicMock()
    repo.get_pending = AsyncMock()
    repo.count_pending = AsyncMock()
    return Scheduler(coordinator=coordinator, repo=repo, interval=0.01)


class TestRunCycle:
    @pytest.mark.asyncio
    async def test_with_pending_file(self, scheduler):
        scheduler.repo.get_pending.return_value = {
            "id": 1, "filename": "f.bin", "size": 100, "sha256": "abc",
            "status": "PENDING", "remote_path": "r", "local_path": "l",
        }
        result = await scheduler.run_cycle()
        assert result is True
        scheduler.coordinator.run.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_without_pending_file(self, scheduler):
        scheduler.repo.get_pending.return_value = None
        result = await scheduler.run_cycle()
        assert result is False
        scheduler.coordinator.run.assert_not_called()

    @pytest.mark.asyncio
    async def test_passes_sync_task(self, scheduler):
        scheduler.repo.get_pending.return_value = {
            "id": 7, "filename": "model.bin", "size": 5000, "sha256": "def",
            "status": "PENDING", "remote_path": "gdrive:path/model.bin",
            "local_path": "/tmp/model.bin",
        }
        await scheduler.run_cycle()
        task = scheduler.coordinator.run.call_args[0][0]
        assert task.file_id == 7
        assert task.filename == "model.bin"
        assert task.size == 5000
        assert task.sha256 == "def"
        assert task.local_path == "/tmp/model.bin"
        assert task.remote_path == "gdrive:path/model.bin"


class TestLoop:
    @pytest.mark.asyncio
    async def test_breaks_when_done(self, scheduler):
        """No pending files + no remaining count = idle."""
        scheduler.repo.get_pending.side_effect = [None]
        scheduler.repo.count_pending.return_value = 0
        await scheduler.loop()
        assert scheduler.coordinator.run.await_count == 0

    @pytest.mark.asyncio
    async def test_processes_then_idle(self, scheduler):
        """One file processed, then nothing left."""
        scheduler.repo.get_pending.side_effect = [
            {
                "id": 1, "filename": "f.bin", "size": 100, "sha256": "abc",
                "status": "PENDING", "remote_path": "r", "local_path": "l",
            },
            None,
        ]
        scheduler.repo.count_pending.return_value = 0
        await scheduler.loop()
        assert scheduler.coordinator.run.await_count == 1

    @pytest.mark.asyncio
    async def test_sleeps_when_still_pending_but_none_returned(self, scheduler):
        """When get_pending returns None but count > 0, scheduler sleeps and retries."""
        scheduler.repo.get_pending.side_effect = [None, None]
        scheduler.repo.count_pending.side_effect = [1, 0]
        await scheduler.loop()
        assert scheduler.coordinator.run.await_count == 0
