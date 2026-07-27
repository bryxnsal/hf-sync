"""File repository — all SQL lives here."""

from __future__ import annotations

from typing import Any

import aiosqlite

from hf_sync.types.enums import Status

_SELECT_PENDING = """
SELECT id, filename, size, sha256, status, remote_path, local_path
FROM files
WHERE status = ?
ORDER BY id ASC
LIMIT 1
"""

_UPDATE_STATUS = "UPDATE files SET status = ?, updated_at = datetime('now') WHERE id = ?"

_INSERT_FILE = """
INSERT INTO files (filename, size, sha256, status, remote_path, local_path)
VALUES (?, ?, ?, ?, ?, ?)
"""

_INSERT_EVENT = "INSERT INTO events (file_id, event, message) VALUES (?, ?, ?)"

_GET_BY_ID = "SELECT id, filename, size, sha256, status, remote_path, local_path FROM files WHERE id = ?"

_GET_BY_NAME = "SELECT id, filename, size, sha256, status, remote_path, local_path FROM files WHERE filename = ?"

_COUNT_PENDING = "SELECT COUNT(*) FROM files WHERE status = ?"


class FileRepository:
    """CRUD and queries for file records."""

    conn: aiosqlite.Connection

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self.conn = conn

    async def get_pending(self) -> dict[str, Any] | None:
        """Return the next pending file, or None."""
        cur = await self.conn.execute(_SELECT_PENDING, (Status.PENDING.value,))
        row = await cur.fetchone()
        if row is None:
            return None
        return dict(row)

    async def get_by_id(self, file_id: int) -> dict[str, Any] | None:
        cur = await self.conn.execute(_GET_BY_ID, (file_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

    async def get_by_name(self, filename: str) -> dict[str, Any] | None:
        cur = await self.conn.execute(_GET_BY_NAME, (filename,))
        row = await cur.fetchone()
        return dict(row) if row else None

    async def insert(self, filename: str, size: int, sha256: str = "",
                     status: str = "PENDING", remote_path: str = "",
                     local_path: str = "") -> int:
        cur = await self.conn.execute(_INSERT_FILE,
                                      (filename, size, sha256, status, remote_path, local_path))
        await self.conn.commit()
        result = cur.lastrowid
        assert result is not None
        return result

    async def update_status(self, file_id: int, status: Status) -> None:
        await self.conn.execute(_UPDATE_STATUS, (status.value, file_id))
        await self.conn.commit()

    async def mark_done(self, file_id: int) -> None:
        await self.update_status(file_id, Status.DONE)

    async def mark_failed(self, file_id: int) -> None:
        await self.conn.execute(_UPDATE_STATUS, (Status.FAILED.value, file_id))
        await self.conn.commit()

    async def add_event(self, file_id: int, event: str, message: str = "") -> None:
        await self.conn.execute(_INSERT_EVENT, (file_id, event, message))
        await self.conn.commit()

    async def count_pending(self) -> int:
        cur = await self.conn.execute(_COUNT_PENDING, (Status.PENDING.value,))
        row = await cur.fetchone()
        return row[0] if row else 0
