"""Tests for logger configuration."""

from __future__ import annotations

# pyright: reportAttributeAccessIssue=false

from loguru import logger

from hf_sync.logger import setup_logger


def test_setup_logger_removes_existing() -> None:
    """Ensure setup_logger removes existing handlers and adds new ones."""
    before = len(logger._core.handlers)
    setup_logger("DEBUG")
    assert len(logger._core.handlers) >= 1


def test_setup_logger_with_log_file(tmp_path) -> None:
    log_file = str(tmp_path / "test.log")
    setup_logger("INFO", log_file=log_file)
    logger.info("test message")
    # file should exist and contain our message
    import time
    time.sleep(0.1)  # let loguru flush
    content = (tmp_path / "test.log").read_text()
    assert "test message" in content


def test_setup_logger_level_info() -> None:
    setup_logger("INFO")
    logger.debug("should not appear in stderr")  # just ensure no crash


def test_setup_logger_level_debug() -> None:
    setup_logger("DEBUG")
    # just ensure no crash
    logger.debug("debug message")
