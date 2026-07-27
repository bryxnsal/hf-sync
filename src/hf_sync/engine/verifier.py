"""Verifier — checks size, existence, status, integrity."""

from __future__ import annotations

from pathlib import Path


class Verifier:
    """Verify downloaded / uploaded file integrity."""

    @staticmethod
    def exists(path: str) -> bool:
        """Check file exists on disk."""
        return Path(path).is_file()

    @staticmethod
    def size_matches(path: str, expected_size: int) -> bool:
        """Check file size matches expected."""
        if not Path(path).is_file():
            return False
        return Path(path).stat().st_size == expected_size

    @staticmethod
    def sha256_matches(path: str, expected_sha: str) -> bool:
        """Check SHA-256 matches."""
        if not expected_sha:
            return True  # skip if no hash provided
        from hf_sync.utils.hashing import sha256

        return sha256(path) == expected_sha

    def verify(self, path: str, expected_size: int = 0, expected_sha: str = "") -> bool:
        """Run all applicable checks."""
        if not self.exists(path):
            return False
        if expected_size and not self.size_matches(path, expected_size):
            return False
        if expected_sha and not self.sha256_matches(path, expected_sha):
            return False
        return True
