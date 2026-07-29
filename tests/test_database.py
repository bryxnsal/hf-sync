"""Tests for Database — SQLModel table definitions and connection."""

from __future__ import annotations

import aiosqlite
from pathlib import Path

import pytest

from hf_sync.database import Database, FileRecord, EventRecord


class TestDatabase:
    def test_init_path(self):
        db = Database(":memory:")
        assert db.path == ":memory:"

    def test_init_default_path(self):
        db = Database()
        assert "state.db" in db.path

    @pytest.mark.asyncio
    async def test_connect_creates_tables(self, tmp_path):
        """Connect creates tables and returns connection."""
        path = str(tmp_path / "test.db")
        db = Database(path)
        conn = await db.connect()
        assert isinstance(conn, aiosqlite.Connection)

        # Verify files table exists
        cur = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in await cur.fetchall()]
        assert "files" in tables
        assert "events" in tables

        await conn.close()

    @pytest.mark.asyncio
    async def test_connect_is_idempotent(self, tmp_path):
        """Calling connect twice should not error."""
        path = str(tmp_path / "test.db")
        db = Database(path)
        conn1 = await db.connect()
        await conn1.close()

        conn2 = await db.connect()
        assert isinstance(conn2, aiosqlite.Connection)
        await conn2.close()

    @pytest.mark.asyncio
    async def test_init_db(self, tmp_path):
        path = str(tmp_path / "init.db")
        await Database.init_db(path)
        assert Path(path).exists()

        # Verify tables
        conn = await aiosqlite.connect(path)
        cur = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='files'"
        )
        assert await cur.fetchone() is not None
        await conn.close()

    @pytest.mark.asyncio
    async def test_connect_returns_row_factory(self, tmp_path):
        path = str(tmp_path / "row_factory.db")
        db = Database(path)
        conn = await db.connect()
        assert conn.row_factory is aiosqlite.Row
        await conn.close()

    @pytest.mark.asyncio
    async def test_connect_creates_parent_dir(self, tmp_path):
        path = str(tmp_path / "nested" / "dir" / "test.db")
        db = Database(path)
        conn = await db.connect()
        assert Path(path).parent.exists()
        await conn.close()

    @pytest.mark.asyncio
    async def test_init_db_creates_parent_dir(self, tmp_path):
        path = str(tmp_path / "nested" / "init.db")
        await Database.init_db(path)
        assert Path(path).parent.exists()


class TestFileRecord:
    def test_defaults(self):
        r = FileRecord(filename="test.bin")
        assert r.filename == "test.bin"
        assert r.size == 0
        assert r.sha256 == ""
        assert r.status == "PENDING"
        assert r.remote_path == ""
        assert r.local_path == ""

    def test_full(self):
        r = FileRecord(
            filename="model.bin", size=1000, sha256="abc", status="DONE",
            remote_path="gdrive:model.bin", local_path="/tmp/model.bin",
        )
        assert r.size == 1000
        assert r.status == "DONE"

    def test_id_none_by_default(self):
        r = FileRecord(filename="f.bin")
        assert r.id is None

    def test_timestamps(self):
        r = FileRecord(filename="f.bin")
        assert r.created_at is not None
        assert r.updated_at is not None


class TestEventRecord:
    def test_defaults(self):
        e = EventRecord(file_id=1, event="download_start")
        assert e.file_id == 1
        assert e.event == "download_start"
        assert e.message == ""
        assert e.timestamp is not None

    def test_full(self):
        e = EventRecord(file_id=2, event="download_done", message="/tmp/f.bin")
        assert e.message == "/tmp/f.bin"
