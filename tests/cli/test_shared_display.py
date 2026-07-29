"""Tests for CLI shared display components."""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

import pytest
from rich.console import Console

from hf_sync.cli import _fmt_elapsed, _FrozenBar, _parse_destination


class TestFmtElapsed:
    def test_seconds(self):
        assert _fmt_elapsed(0) == "0:00"
        assert _fmt_elapsed(5) == "0:05"
        assert _fmt_elapsed(59) == "0:59"

    def test_minutes(self):
        assert _fmt_elapsed(60) == "1:00"
        assert _fmt_elapsed(3599) == "59:59"

    def test_hours(self):
        assert _fmt_elapsed(3600) == "1:00:00"
        assert _fmt_elapsed(3661) == "1:01:01"
        assert _fmt_elapsed(86399) == "23:59:59"


class TestFrozenBar:
    def test_success_renders_all_fields(self):
        bar = _FrozenBar(1, 54, "model.safetensors", "15.8GB", "1:23:45", "OK", True)
        buf = StringIO()
        c = Console(file=buf, width=120, force_terminal=False)
        c.print(bar)
        out = buf.getvalue()
        assert "[1/54]" in out
        assert "model.safetensors" in out
        assert "15.8GB" in out
        assert "100%" in out
        assert "1:23:45" in out
        assert "OK" in out

    def test_error_renders_message_no_pct(self):
        bar = _FrozenBar(2, 54, "bad.bin", "1.2GB", "0:00:15", "Connection refused", False)
        buf = StringIO()
        c = Console(file=buf, width=120, force_terminal=False)
        c.print(bar)
        out = buf.getvalue()
        assert "[2/54]" in out
        assert "bad.bin" in out
        assert "1.2GB" in out
        assert "0:00:15" in out
        assert "Connection refused" in out
        assert "100" not in out

    def test_success_color_green(self):
        bar = _FrozenBar(1, 1, "f", "1B", "0:01", "OK", True)
        buf = StringIO()
        c = Console(file=buf, width=80, force_terminal=True, color_system="standard")
        c.print(bar)
        assert "\x1b[32m" in buf.getvalue()

    def test_error_color_red(self):
        bar = _FrozenBar(1, 1, "f", "1B", "0:01", "fail", False)
        buf = StringIO()
        c = Console(file=buf, width=80, force_terminal=True, color_system="standard")
        c.print(bar)
        assert "\x1b[31m" in buf.getvalue()

    def test_success_emoji(self):
        bar = _FrozenBar(1, 1, "f", "1B", "0:01", "OK", True)
        buf = StringIO()
        c = Console(file=buf, width=80, force_terminal=False)
        c.print(bar)
        assert "\u2713" in buf.getvalue()

    def test_error_emoji(self):
        bar = _FrozenBar(1, 1, "f", "1B", "0:01", "fail", False)
        buf = StringIO()
        c = Console(file=buf, width=80, force_terminal=False)
        c.print(bar)
        assert "\u2717" in buf.getvalue()

    def test_narrow_width_truncates(self):
        bar = _FrozenBar(1, 100, "very-long-filename.bin", "15.8GB", "1:00:00", "OK", True)
        buf = StringIO()
        c = Console(file=buf, width=40, force_terminal=False)
        c.print(bar)
        assert buf.getvalue()


class TestParseDestination:
    """_parse_destination splits remote:path."""

    def test_with_colon(self):
        r, p = _parse_destination("gdrive:path/to/model")
        assert r == "gdrive"
        assert p == "path/to/model"

    def test_remote_only(self):
        r, p = _parse_destination("gdrive")
        assert r == "gdrive"
        assert p == ""

    def test_empty(self):
        r, p = _parse_destination("")
        assert r == ""
        assert p == ""
