"""Tests for database."""

from hf_sync.database import Database


def test_database_init() -> None:
    db = Database(":memory:")
    assert db.path == ":memory:"
