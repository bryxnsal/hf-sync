"""Tests for utility modules: bytes, eta, hashing, paths, subprocess."""

from __future__ import annotations

from pathlib import Path

from hf_sync.utils.bytes import human_size
from hf_sync.utils.eta import format_eta
from hf_sync.utils.hashing import sha256
from hf_sync.utils.paths import data_path, temp_path
from hf_sync.utils.subprocess import run


# --- bytes ---

def test_human_size_bytes() -> None:
    assert human_size(0) == "0.0B"
    assert human_size(512) == "512.0B"
    assert human_size(1023) == "1023.0B"


def test_human_size_kb() -> None:
    assert human_size(1024) == "1.0KB"
    assert human_size(1536) == "1.5KB"
    assert human_size(1024 * 1024 - 1) == "1024.0KB"


def test_human_size_mb() -> None:
    assert human_size(1024 * 1024) == "1.0MB"
    assert human_size(1024 * 1024 * 10) == "10.0MB"


def test_human_size_gb() -> None:
    assert human_size(1024**3) == "1.0GB"
    assert human_size(2 * 1024**3) == "2.0GB"


def test_human_size_tb() -> None:
    assert human_size(1024**4) == "1.0TB"


def test_human_size_pb() -> None:
    assert human_size(1024**5) == "1.0PB"  # 1024^5 = 1PB
    assert human_size(1024**5 * 2) == "2.0PB"


# --- eta ---

def test_format_eta_seconds() -> None:
    assert format_eta(0) == "0s"
    assert format_eta(30) == "30s"
    assert format_eta(59) == "59s"


def test_format_eta_minutes() -> None:
    assert format_eta(60) == "1m"
    assert format_eta(120) == "2m"
    assert format_eta(3599) == "60m"


def test_format_eta_hours() -> None:
    assert format_eta(3600) == "1.0h"
    assert format_eta(5400) == "1.5h"
    assert format_eta(86400) == "24.0h"


# --- hashing ---

def test_sha256(tmp_path: Path) -> None:
    f = tmp_path / "test.bin"
    f.write_bytes(b"hello world")
    # known sha256 of "hello world"
    expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert sha256(str(f)) == expected


def test_sha256_empty(tmp_path: Path) -> None:
    f = tmp_path / "empty.bin"
    f.write_bytes(b"")
    expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert sha256(str(f)) == expected


def test_sha256_large_chunk_boundary(tmp_path: Path) -> None:
    """Verify hashing works with data > 64KB chunk size."""
    f = tmp_path / "large.bin"
    data = b"x" * 70000  # 70KB > 65536 chunk
    f.write_bytes(data)
    import hashlib
    expected = hashlib.sha256(data).hexdigest()
    assert sha256(str(f)) == expected


# --- paths ---

def test_temp_path() -> None:
    assert str(temp_path()) == "temp"


def test_data_path() -> None:
    assert str(data_path()) == "data"


# --- subprocess ---

def test_subprocess_run_echo() -> None:
    result = run(["echo", "hello"])
    assert result.returncode == 0
    assert "hello" in result.stdout


def test_subprocess_run_false() -> None:
    result = run(["false"])
    assert result.returncode != 0
