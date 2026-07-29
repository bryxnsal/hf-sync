"""Tests for models, DTOs, enums, and constants."""

from __future__ import annotations

from hf_sync.constants import APP_DIRS, APP_NAME, DB_INIT_SQL, VERSION
from hf_sync.models import DownloadTask, HFFile, ProgressSnapshot, RepositoryInfo
from hf_sync.types.dto import DoctorReport, DryRunReport, RepoInfoDTO, SyncTask
from hf_sync.types.enums import Status


# --- constants ---

def test_app_name() -> None:
    assert APP_NAME == "hf-sync"


def test_version() -> None:
    assert VERSION == "0.1.0"


def test_app_dirs() -> None:
    assert "temp" in APP_DIRS


def test_db_init_sql_contains_tables() -> None:
    assert "CREATE TABLE IF NOT EXISTS files" in DB_INIT_SQL
    assert "CREATE TABLE IF NOT EXISTS events" in DB_INIT_SQL


# --- enums ---

def test_status_values() -> None:
    assert Status.PENDING.value == "PENDING"
    assert Status.DOWNLOADING.value == "DOWNLOADING"
    assert Status.DOWNLOADED.value == "DOWNLOADED"
    assert Status.UPLOADING.value == "UPLOADING"
    assert Status.VERIFYING.value == "VERIFYING"
    assert Status.DONE.value == "DONE"
    assert Status.FAILED.value == "FAILED"


def test_status_is_str_enum() -> None:
    assert issubclass(Status, str)


# --- models ---

class TestHFFile:
    def test_defaults(self) -> None:
        f = HFFile(filename="test.bin")
        assert f.filename == "test.bin"
        assert f.size == 0
        assert f.sha256 == ""
        assert f.download_url == ""

    def test_full(self) -> None:
        f = HFFile(filename="a.bin", size=1024, sha256="abc123", download_url="https://example.com/a.bin")
        assert f.size == 1024
        assert f.sha256 == "abc123"
        assert f.download_url == "https://example.com/a.bin"


class TestDownloadTask:
    def test_defaults(self) -> None:
        t = DownloadTask(file_id=1, source_url="http://example.com/f", dest_path="/tmp/f")
        assert t.file_id == 1
        assert t.source_url == "http://example.com/f"
        assert t.dest_path == "/tmp/f"
        assert t.size == 0
        assert t.gid == ""

    def test_all_fields(self) -> None:
        t = DownloadTask(file_id=2, source_url="u", dest_path="d", size=42, gid="abc")
        assert t.size == 42
        assert t.gid == "abc"


class TestRepositoryInfo:
    def test_defaults(self) -> None:
        r = RepositoryInfo(repo_id="org/repo")
        assert r.repo_id == "org/repo"
        assert r.files == []

    def test_with_files(self) -> None:
        files = [HFFile(filename="a.bin"), HFFile(filename="b.bin")]
        r = RepositoryInfo(repo_id="org/repo", files=files)
        assert len(r.files) == 2


class TestProgressSnapshot:
    def test_defaults(self) -> None:
        s = ProgressSnapshot()
        assert s.stage == ""
        assert s.current == 0
        assert s.total == 0
        assert s.elapsed == 0.0
        assert s.file == ""

    def test_full(self) -> None:
        s = ProgressSnapshot(stage="download", current=50, total=100, elapsed=12.5, file="test.bin")
        assert s.stage == "download"
        assert s.current == 50
        assert s.elapsed == 12.5


# --- DTOs ---

class TestSyncTask:
    def test_minimal(self) -> None:
        t = SyncTask(file_id=1, filename="f", source_url="u", local_path="l", remote_path="r")
        assert t.size == 0
        assert t.sha256 == ""
        assert t.status == "PENDING"

    def test_full(self) -> None:
        t = SyncTask(file_id=1, filename="f", source_url="u", local_path="l",
                      remote_path="r", size=42, sha256="abc", status="DONE")
        assert t.size == 42
        assert t.sha256 == "abc"
        assert t.status == "DONE"


class TestRepoInfoDTO:
    def test_defaults(self) -> None:
        r = RepoInfoDTO(repo_id="org/repo")
        assert r.accessible is False


class TestDoctorReport:
    def test_defaults(self) -> None:
        r = DoctorReport()
        assert r.aria2 is False
        assert not r.aria2_error

    def test_partial_ok(self) -> None:
        r = DoctorReport(aria2=True, rclone=True, permissions_ok=True)
        assert r.aria2
        assert r.rclone
        assert r.permissions_ok
        assert not r.hf_token


class TestDryRunReport:
    def test_defaults(self) -> None:
        r = DryRunReport()
        assert r.repo_id == ""

    def test_large_file_detected(self) -> None:
        r = DryRunReport(repo_id="org/repo", largest_file_name="big.bin", largest_file_size=1_000_000_000)
        assert r.largest_file_name == "big.bin"
        assert r.largest_file_size == 1_000_000_000
