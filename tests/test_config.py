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
