"""Tests for Settings (pydantic-settings).

Uses _env_file=None to skip reading the real .env config file,
so tests work regardless of what's in ~/.config/hf-sync/.env.
"""
# pyright: reportCallIssue=false

from __future__ import annotations

from hf_sync.config import Settings


class TestSettings:
    def test_default_aria2_url(self):
        s = Settings(_env_file=None)
        assert s.aria2_rpc_url == "http://localhost:6800/jsonrpc"

    def test_default_log_level(self):
        s = Settings(_env_file=None)
        assert s.log_level == "INFO"

    def test_default_aria2_secret(self):
        s = Settings(_env_file=None)
        assert s.aria2_rpc_secret == ""

    def test_default_hf_token(self):
        s = Settings(_env_file=None)
        assert s.hf_token == ""

    def test_default_hf_repo_id(self):
        s = Settings(_env_file=None)
        assert s.hf_repo_id == ""

    def test_default_rclone_remote(self):
        s = Settings(_env_file=None)
        assert s.rclone_remote == ""

    def test_default_rclone_path(self):
        s = Settings(_env_file=None)
        assert s.rclone_path == ""

    def test_db_path_contains_state_db(self):
        s = Settings(_env_file=None)
        assert "state.db" in s.db_path

    def test_temp_dir_contains_temp(self):
        s = Settings(_env_file=None)
        assert "temp" in s.temp_dir

    def test_custom_values(self):
        s = Settings(
            _env_file=None,
            hf_token="hf_test123",
            aria2_rpc_url="http://192.168.1.100:6800/jsonrpc",
            log_level="DEBUG",
            db_path="/custom/path/db.sqlite",
        )
        assert s.hf_token == "hf_test123"
        assert s.aria2_rpc_url == "http://192.168.1.100:6800/jsonrpc"
        assert s.log_level == "DEBUG"
        assert s.db_path == "/custom/path/db.sqlite"


class TestDbFallback:
    """Tests for DB config fallback (config module-level logic)."""

    def test_apply_db_overrides_no_db(self, tmp_path):
        from hf_sync.config import _apply_db_overrides

        s = Settings(_env_file=None, db_path=str(tmp_path / "no.db"))
        _apply_db_overrides(s)
        # No crash, defaults unchanged
        assert s.hf_repo_id == ""
        assert s.aria2_rpc_url == "http://localhost:6800/jsonrpc"

    def test_apply_db_overrides_applies(self, tmp_path):
        from hf_sync.config import _apply_db_overrides
        from hf_sync.database import Database
        import asyncio

        db_path = str(tmp_path / "test.db")
        asyncio.run(Database.init_db(db_path))
        import sqlite3

        conn = sqlite3.connect(db_path)
        conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ("hf_repo_id", "org/repo"))
        conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ("aria2_rpc_url", "http://custom:6800"))
        conn.commit()
        conn.close()

        s = Settings(_env_file=None, db_path=db_path)
        _apply_db_overrides(s)
        assert s.hf_repo_id == "org/repo"
        assert s.aria2_rpc_url == "http://custom:6800"

    def test_apply_db_overrides_does_not_override_env(self, tmp_path):
        """Values set via env/.env should NOT be overridden by DB."""
        from hf_sync.config import _apply_db_overrides
        from hf_sync.database import Database
        import asyncio

        db_path = str(tmp_path / "env_override.db")
        asyncio.run(Database.init_db(db_path))
        import sqlite3

        conn = sqlite3.connect(db_path)
        conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ("aria2_rpc_url", "http://db:6800"))
        conn.commit()
        conn.close()

        s = Settings(_env_file=None, db_path=db_path, aria2_rpc_url="http://env:6800")
        _apply_db_overrides(s)
        assert s.aria2_rpc_url == "http://env:6800"
