"""Byte formatting utilities."""


def human_size(bytes_: int) -> str:
    """Format bytes to human-readable string."""
    remaining = float(bytes_)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if remaining < 1024:
            return f"{remaining:.1f}{unit}"
        remaining /= 1024
    return f"{remaining:.1f}PB"
