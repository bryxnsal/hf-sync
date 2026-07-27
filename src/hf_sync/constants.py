"""Project constants."""

APP_NAME = "hf-sync"
VERSION = "0.1.0"
APP_DIRS = ("data", "data/logs", "temp")
DB_INIT_SQL = """
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
