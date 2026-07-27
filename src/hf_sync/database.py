"""SQLModel table definitions + Database helpers.

Only two tables: files and events.
All raw SQL lives in repositories/ — this module owns schema only.
"""

from __future__ import annotations

from datetime import datetime, timezone
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
        conn = await aiosqlite.connect(self.path)
        conn.row_factory = aiosqlite.Row
        await conn.executescript(_SCHEMA_SQL)
        await conn.commit()
        return conn

    @staticmethod
    async def init_db(path: str = "data/state.db") -> None:
        """Idempotent schema creation (called from CLI init)."""
        conn = await aiosqlite.connect(path)
        await conn.executescript(_SCHEMA_SQL)
        await conn.commit()
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
"""
