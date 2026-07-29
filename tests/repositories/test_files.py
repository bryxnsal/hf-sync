"""Tests for FileRepository — async SQL queries."""

from __future__ import annotations

import aiosqlite
import pytest

from hf_sync.repositories.files import FileRepository
from hf_sync.types.enums import Status

_SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    size INTEGER DEFAULT 0,
    sha256 TEXT DEFAULT '',
    status TEXT DEFAULT 'PENDING',
    remote_path TEXT DEFAULT '',
    local_path TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    event TEXT NOT NULL,
    message TEXT DEFAULT '',
    timestamp TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (file_id) REFERENCES files(id)
);
"""


@pytest.fixture
async def repo():
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.executescript(_SCHEMA)
    await conn.commit()
    yield FileRepository(conn)
    await conn.close()


@pytest.mark.asyncio
async def test_get_pending_empty(repo):
    assert await repo.get_pending() is None


@pytest.mark.asyncio
async def test_insert_and_get_pending(repo):
    fid = await repo.insert("test.bin", 1024, "abc123")
    assert isinstance(fid, int)
    row = await repo.get_pending()
    assert row is not None
    assert row["filename"] == "test.bin"
    assert row["size"] == 1024
    assert row["sha256"] == "abc123"
    assert row["status"] == Status.PENDING.value


@pytest.mark.asyncio
async def test_get_by_id(repo):
    fid = await repo.insert("f.bin", 512)
    row = await repo.get_by_id(fid)
    assert row is not None
    assert row["filename"] == "f.bin"
    assert row["size"] == 512


@pytest.mark.asyncio
async def test_get_by_id_missing(repo):
    assert await repo.get_by_id(999) is None


@pytest.mark.asyncio
async def test_get_by_name(repo):
    fid = await repo.insert("unique.bin", 256)
    row = await repo.get_by_name("unique.bin")
    assert row is not None
    assert row["id"] == fid


@pytest.mark.asyncio
async def test_get_by_name_missing(repo):
    assert await repo.get_by_name("nonexistent") is None


@pytest.mark.asyncio
async def test_update_status(repo):
    fid = await repo.insert("f.bin", 100)
    await repo.update_status(fid, Status.DOWNLOADING)
    row = await repo.get_by_id(fid)
    assert row["status"] == Status.DOWNLOADING.value


@pytest.mark.asyncio
async def test_mark_done(repo):
    fid = await repo.insert("f.bin", 100)
    await repo.mark_done(fid)
    row = await repo.get_by_id(fid)
    assert row["status"] == Status.DONE.value


@pytest.mark.asyncio
async def test_mark_failed(repo):
    fid = await repo.insert("f.bin", 100)
    await repo.mark_failed(fid)
    row = await repo.get_by_id(fid)
    assert row["status"] == Status.FAILED.value


@pytest.mark.asyncio
async def test_count_pending_empty(repo):
    assert await repo.count_pending() == 0


@pytest.mark.asyncio
async def test_count_pending(repo):
    await repo.insert("a.bin", 10)
    await repo.insert("b.bin", 20)
    assert await repo.count_pending() == 2


@pytest.mark.asyncio
async def test_insert_with_custom_fields(repo):
    fid = await repo.insert("f.bin", 100, status="DOWNLOADING", remote_path="r", local_path="l")
    row = await repo.get_by_id(fid)
    assert row["status"] == "DOWNLOADING"
    assert row["remote_path"] == "r"
    assert row["local_path"] == "l"


@pytest.mark.asyncio
async def test_add_event(repo):
    fid = await repo.insert("f.bin", 100)
    await repo.add_event(fid, "test_event", "test message")
    cur = await repo.conn.execute(
        "SELECT file_id, event, message FROM events WHERE file_id = ?", (fid,)
    )
    row = await cur.fetchone()
    assert row is not None
    assert row["event"] == "test_event"
    assert row["message"] == "test message"


@pytest.mark.asyncio
async def test_pending_not_include_done(repo):
    await repo.insert("a.bin", 10)
    fid = await repo.insert("b.bin", 20)
    await repo.mark_done(fid)
    row = await repo.get_pending()
    assert row is not None
    assert row["filename"] == "a.bin"


@pytest.mark.asyncio
async def test_get_pending_ordered_by_id(repo):
    await repo.insert("z.bin", 10)
    await repo.insert("a.bin", 20)
    row = await repo.get_pending()
    assert row["filename"] == "z.bin"
