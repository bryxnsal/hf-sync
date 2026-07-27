"""ETA calculation utilities."""


def format_eta(seconds: float) -> str:
    """Format seconds to human-readable ETA."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.0f}m"
    hours = minutes / 60
    return f"{hours:.1f}h"
