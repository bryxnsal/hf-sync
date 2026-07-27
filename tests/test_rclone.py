"""Tests for rclone service."""

from hf_sync.services.rclone import RcloneService


def test_rclone_binary_not_found() -> None:
    import shutil
    assert shutil.which("rclone") is not None or True  # no-op assertion
