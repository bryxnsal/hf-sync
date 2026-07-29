"""SQLModel table definitions + Database helpers.

Only two tables: files and events.
All raw SQL lives in repositories/ — this module owns schema only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar

import aiosqlite
from sqlmodel import Field, SQLModel


class FileRecord(SQLModel, table=True):
    """Tracked file in the sync pipeline."""

    __tablename__: ClassVar[str] = "files"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: int | None = Field(default=None, primary_key=True)
    filename: str
    size: int = 0
    sha256: str = ""
    status: str = "PENDING"
    remote_path: str = ""
    local_path: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EventRecord(SQLModel, table=True):
    """Audit event for a file's lifecycle."""

    __tablename__: ClassVar[str] = "events"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: int | None = Field(default=None, primary_key=True)
    file_id: int = Field(foreign_key="files.id")
    event: str
    message: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Database:
    """Manage the SQLite connection and schema."""

    path: str

    def __init__(self, path: str = "data/state.db") -> None:
        self.path = path

    async def connect(self) -> aiosqlite.Connection:
        """Open (or create) the database and ensure tables exist."""
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        conn = await aiosqlite.connect(self.path)
        conn.row_factory = aiosqlite.Row
        await conn.executescript(_SCHEMA_SQL)
        await conn.commit()
        return conn

    @staticmethod
    async def init_db(path: str = "data/state.db") -> None:
        """Idempotent schema creation (called from CLI init)."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = await aiosqlite.connect(path)
        await conn.executescript(_SCHEMA_SQL)
        await conn.commit()
        await conn.close()

    async def get_config(self, key: str) -> str | None:
        """Get a config value by key."""
        conn = await self.connect()
        try:
            cur = await conn.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = await cur.fetchone()
            return row[0] if row else None
        finally:
            await conn.close()

    async def set_config(self, key: str, value: str) -> None:
        """Upsert a config value."""
        conn = await self.connect()
        try:
            await conn.execute(
                "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
            await conn.commit()
        finally:
            await conn.close()


_SCHEMA_SQL = """
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

CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def sync_get_config(db_path: str, key: str) -> str | None:
    """Synchronous key lookup for startup — uses stdlib sqlite3.
    Returns None if DB/table doesn't exist yet or key not found."""
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except (sqlite3.OperationalError, Exception):
        return None
