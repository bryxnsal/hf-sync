"""Tests for config."""

from hf_sync.config import Settings


def test_settings_defaults() -> None:
    s = Settings()
    assert s.aria2_rpc_url == "http://localhost:6800/jsonrpc"
    assert s.log_level == "INFO"
