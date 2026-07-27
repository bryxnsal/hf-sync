"""Logging configuration via loguru."""

import sys
from pathlib import Path

from loguru import logger


def setup_logger(level: str = "INFO", log_file: str | None = None) -> None:
    """Configure loguru sinks."""
    logger.remove()

    logger.add(sys.stderr, level=level, format="<level>{level: <8}</level> | {message}")

    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(path),
            level=level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            rotation="10 MB",
            retention=7,
        )
