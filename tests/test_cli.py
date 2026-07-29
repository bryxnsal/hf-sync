"""Tests for CLI display components."""

from __future__ import annotations

from hf_sync.cli import _fmt_elapsed, _FrozenBar


def test_fmt_elapsed_seconds() -> None:
    """Seconds-only -> MM:SS."""
    assert _fmt_elapsed(0) == "0:00"
    assert _fmt_elapsed(5) == "0:05"
    assert _fmt_elapsed(59) == "0:59"
    assert _fmt_elapsed(60) == "1:00"
    assert _fmt_elapsed(3599) == "59:59"


def test_fmt_elapsed_hours() -> None:
    """One hour+ -> HH:MM:SS."""
    assert _fmt_elapsed(3600) == "1:00:00"
    assert _fmt_elapsed(3661) == "1:01:01"
    assert _fmt_elapsed(86399) == "23:59:59"


def test_frozen_bar_success_plain() -> None:
    """_FrozenBar success renders all expected fields as plain text."""
    bar = _FrozenBar(1, 54, "model.safetensors", "15.8GB", "1:23:45", "OK", True)

    from io import StringIO

    from rich.console import Console

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


def test_frozen_bar_error_plain() -> None:
    """_FrozenBar error shows error message, no percentage."""
    bar = _FrozenBar(2, 54, "bad_file.bin", "1.2GB", "0:00:15", "Connection refused", False)

    from io import StringIO

    from rich.console import Console

    buf = StringIO()
    c = Console(file=buf, width=120, force_terminal=False)
    c.print(bar)
    out = buf.getvalue()

    assert "[2/54]" in out
    assert "bad_file.bin" in out
    assert "1.2GB" in out
    assert "0:00:15" in out
    assert "Connection refused" in out
    assert "100" not in out


def test_frozen_bar_color_success() -> None:
    """Green ANSI for success."""
    bar = _FrozenBar(1, 1, "f", "1B", "0:01", "OK", True)

    from io import StringIO

    from rich.console import Console

    buf = StringIO()
    c = Console(file=buf, width=80, force_terminal=True, color_system="standard")
    c.print(bar)
    out = buf.getvalue()

    assert "\x1b[32m" in out  # green


def test_frozen_bar_color_error() -> None:
    """Red ANSI for error."""
    bar = _FrozenBar(1, 1, "f", "1B", "0:01", "fail", False)

    from io import StringIO

    from rich.console import Console

    buf = StringIO()
    c = Console(file=buf, width=80, force_terminal=True, color_system="standard")
    c.print(bar)
    out = buf.getvalue()

    assert "\x1b[31m" in out  # red
