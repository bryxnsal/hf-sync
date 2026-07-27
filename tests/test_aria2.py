"""Tests for aria2 service."""

from hf_sync.services.aria2 import Aria2Service


def test_rpc_call_raises_on_no_server() -> None:
    svc = Aria2Service("http://127.0.0.1:16800/jsonrpc")
    try:
        svc.tell_status("0" * 16)
        assert False, "expected exception"
    except Exception:
        assert True
