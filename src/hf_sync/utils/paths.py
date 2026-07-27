"""Path utilities."""

from pathlib import Path


def temp_path() -> Path:
    """Return the temp directory path."""
    return Path("temp")

def data_path() -> Path:
    """Return the data directory path."""
    return Path("data")
