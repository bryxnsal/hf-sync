"""Tests for Aria2Service — JSON-RPC client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from hf_sync.services.aria2 import Aria2Service


@pytest.fixture
def svc():
    return Aria2Service("http://localhost:16800/jsonrpc", secret="mytoken")


class TestInit:
    def test_default_url(self):
        svc = Aria2Service()
        assert svc.url == "http://localhost:6800/jsonrpc"
        assert svc._token == ""

    def test_with_secret(self):
        svc = Aria2Service(secret="sec")
        assert svc._token == "token:sec"

    def test_custom_url(self):
        svc = Aria2Service(url="http://127.0.0.1:6800/jsonrpc", secret="t")
        assert svc.url == "http://127.0.0.1:6800/jsonrpc"


class TestRpcCall:
    def test_passes_token_in_params(self, svc):
        with patch("httpx.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            mock_post.return_value.json.return_value = {"result": "gid"}
            svc.add_uri("http://example.com/f.bin")
            payload = mock_post.call_args[1]["json"]
            assert "token:mytoken" in payload["params"]

    def test_no_token_when_secret_empty(self):
        svc = Aria2Service()
        with patch("httpx.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            mock_post.return_value.json.return_value = {"result": "gid"}
            svc.add_uri("http://example.com/f.bin")
            payload = mock_post.call_args[1]["json"]
            assert not any("token:" in str(p) for p in payload["params"])

    def test_raises_on_rpc_error(self, svc):
        with patch("httpx.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            mock_post.return_value.json.return_value = {
                "error": {"code": 1, "message": "Not found"},
            }
            with pytest.raises(RuntimeError, match="Not found"):
                svc.tell_status("gid123")

    def test_raises_on_connection_error(self, svc):
        with patch("httpx.post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")
            with pytest.raises(httpx.ConnectError):
                svc.tell_status("gid123")


class TestMethods:
    def test_add_uri(self, svc):
        with patch("httpx.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            mock_post.return_value.json.return_value = {"result": "gid123"}
            gid = svc.add_uri("http://example.com/f.bin", {"dir": "/tmp"})
            assert gid == "gid123"
            args, kwargs = mock_post.call_args
            assert args[0] == "http://localhost:16800/jsonrpc"
            payload = kwargs["json"]
            assert payload["method"] == "aria2.addUri"
            assert payload["params"][1] == ["http://example.com/f.bin"]

    def test_tell_status(self, svc):
        with patch("httpx.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            mock_post.return_value.json.return_value = {"result": {"status": "active"}}
            status = svc.tell_status("gid123")
            assert status == {"status": "active"}

    def test_pause(self, svc):
        with patch("httpx.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            mock_post.return_value.json.return_value = {"result": "OK"}
            assert svc.pause("gid123") == "OK"

    def test_resume(self, svc):
        with patch("httpx.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            mock_post.return_value.json.return_value = {"result": "OK"}
            assert svc.resume("gid123") == "OK"

    def test_remove(self, svc):
        with patch("httpx.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            mock_post.return_value.json.return_value = {"result": "OK"}
            assert svc.remove("gid123") == "OK"

    def test_get_version(self, svc):
        with patch("httpx.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            mock_post.return_value.json.return_value = {
                "result": {"version": "1.37.0", "enabledFeatures": ["Async DNS"]},
            }
            v = svc.get_version()
            assert v["version"] == "1.37.0"
