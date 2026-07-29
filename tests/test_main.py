"""Tests for __main__ entry point."""

from __future__ import annotations

import pytest
import runpy


def test_main_import() -> None:
    """__main__.py only imports main from cli — verify it's importable."""
    from hf_sync.cli import main  # noqa: F401
    assert main is not None


def test_main_run_module() -> None:
    """Cover the if __name__ == "__main__" guard by running as module."""
    # runpy.run_module with run_name="__main__" triggers the guard
    with pytest.raises(SystemExit):
        runpy.run_module("hf_sync.__main__", run_name="__main__")
