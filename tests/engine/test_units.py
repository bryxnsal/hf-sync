"""Tests for engine components: Cleanup, Verifier, Downloader, Uploader."""

from __future__ import annotations

from hf_sync.engine.cleanup import Cleanup
from hf_sync.engine.verifier import Verifier


# --- Cleanup ---

class TestCleanup:
    def test_remove_local_existing_file(self, tmp_path) -> None:
        f = tmp_path / "test.bin"
        f.write_bytes(b"data")
        assert f.is_file()
        Cleanup.remove_local(str(f))
        assert not f.exists()

    def test_remove_local_nonexistent(self) -> None:
        """Should not raise on missing file."""
        Cleanup.remove_local("/tmp/nonexistent-file-12345")
        # no exception = pass

    def test_remove_local_empty_string(self) -> None:
        """Should not raise on empty string (path is '')."""
        Cleanup.remove_local("")
        # no exception = pass


# --- Verifier ---

class TestVerifier:
    v: Verifier = Verifier()

    def setup_method(self) -> None:
        self.v = Verifier()

    def test_exists_yes(self, tmp_path) -> None:
        f = tmp_path / "exists.bin"
        f.write_bytes(b"x")
        assert self.v.exists(str(f))

    def test_exists_no(self) -> None:
        assert not self.v.exists("/nonexistent")

    def test_size_matches_ok(self, tmp_path) -> None:
        f = tmp_path / "size.bin"
        f.write_bytes(b"hello")
        assert self.v.size_matches(str(f), 5)

    def test_size_matches_wrong(self, tmp_path) -> None:
        f = tmp_path / "size.bin"
        f.write_bytes(b"hello")
        assert not self.v.size_matches(str(f), 10)

    def test_size_matches_missing(self) -> None:
        assert not self.v.size_matches("/nonexistent", 100)

    def test_sha256_matches_no_hash_expected(self) -> None:
        """When expected_sha is empty, sha256 check is skipped."""
        assert self.v.sha256_matches("any/path", "")
        # doesn't matter if file exists — function returns True early

    def test_sha256_matches_ok(self, tmp_path) -> None:
        f = tmp_path / "hash.bin"
        f.write_bytes(b"hello world")
        expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        assert self.v.sha256_matches(str(f), expected)

    def test_sha256_matches_fail(self, tmp_path) -> None:
        f = tmp_path / "hash.bin"
        f.write_bytes(b"hello world")
        assert not self.v.sha256_matches(str(f), "0000")

    def test_verify_all_pass(self, tmp_path) -> None:
        import hashlib
        data = b"test data"
        f = tmp_path / "all.bin"
        f.write_bytes(data)
        expected_sha = hashlib.sha256(data).hexdigest()
        assert self.v.verify(str(f), expected_size=len(data), expected_sha=expected_sha)

    def test_verify_missing_file(self) -> None:
        assert not self.v.verify("/nonexistent", expected_size=100)

    def test_verify_size_mismatch(self, tmp_path) -> None:
        f = tmp_path / "size.bin"
        f.write_bytes(b"actual data")
        assert not self.v.verify(str(f), expected_size=999)

    def test_verify_sha_mismatch(self, tmp_path) -> None:
        f = tmp_path / "sha.bin"
        f.write_bytes(b"data")
        assert not self.v.verify(str(f), expected_size=4, expected_sha="badbad")
