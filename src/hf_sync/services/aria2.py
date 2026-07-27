"""Aria2 JSON-RPC client.

No business logic — only transport.
Methods: add_uri, tell_status, pause, resume, remove.
"""

from __future__ import annotations

from typing import Any

import httpx


class Aria2Service:
    """Low-level aria2 RPC client."""

    url: str
    _token: str

    def __init__(self, url: str = "http://localhost:6800/jsonrpc", secret: str = "") -> None:
        self.url = url
        self._token = f"token:{secret}" if secret else ""

    def _call(self, method: str, params: list[object] | None = None) -> Any:
        """Execute a JSON-RPC call against aria2."""
        payload: dict[str, object] = {
            "jsonrpc": "2.0",
            "id": "hf-sync",
            "method": method,
            "params": ([self._token] if self._token else []) + (params or []),
        }
        resp = httpx.post(self.url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"aria2 RPC error: {data['error']}")
        return data.get("result", {})

    def add_uri(self, uri: str, options: dict[str, object] | None = None) -> str:
        """Add a download URI, return GID."""
        result = self._call("aria2.addUri", [[uri], options or {}])
        return str(result)

    def tell_status(self, gid: str) -> dict[str, str]:
        """Return status dict for a GID."""
        result = self._call("aria2.tellStatus", [gid])
        return dict(result)

    def pause(self, gid: str) -> str:
        """Pause a download."""
        result = self._call("aria2.pause", [gid])
        return str(result)

    def resume(self, gid: str) -> str:
        """Resume a paused download."""
        result = self._call("aria2.unpause", [gid])
        return str(result)

    def remove(self, gid: str) -> str:
        """Remove a download (and its temp data)."""
        result = self._call("aria2.remove", [gid])
        return str(result)
