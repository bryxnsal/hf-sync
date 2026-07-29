"""Tests for Downloader — wraps Aria2Service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hf_sync.engine.downloader import Downloader


@pytest.fixture
def mock_aria2():
    svc = MagicMock()
    svc.add_uri.return_value = "gid123"
    return svc


@pytest.fixture
def downloader(mock_aria2):
    return Downloader(mock_aria2)


class TestDownload:
    def test_returns_gid(self, downloader, mock_aria2):
        gid = downloader.download("http://example.com/f.bin", "/tmp/dir/f.bin")
        assert gid == "gid123"

    def test_passes_uri_and_options(self, downloader, mock_aria2):
        downloader.download("http://example.com/f.bin", "/tmp/dir/f.bin")
        args, _ = mock_aria2.add_uri.call_args
        assert args[0] == "http://example.com/f.bin"
        assert args[1]["dir"] == "/tmp/dir"
        assert args[1]["out"] == "f.bin"


class TestWaitForCompletion:
    def test_complete(self, downloader, mock_aria2):
        mock_aria2.tell_status.return_value = {"status": "complete"}
        result = downloader.wait_for_completion("gid123")
        assert result["status"] == "complete"

    def test_error(self, downloader, mock_aria2):
        mock_aria2.tell_status.return_value = {"status": "error"}
        result = downloader.wait_for_completion("gid123")
        assert result["status"] == "error"

    def test_removed(self, downloader, mock_aria2):
        mock_aria2.tell_status.return_value = {"status": "removed"}
        result = downloader.wait_for_completion("gid123")
        assert result["status"] == "removed"

    @patch("time.sleep")
    def test_polls_until_complete(self, mock_sleep, downloader, mock_aria2):
        mock_aria2.tell_status.side_effect = [
            {
                "status": "active",
                "completedLength": "50",
                "totalLength": "100",
                "downloadSpeed": "1000",
            },
            {"status": "complete"},
        ]
        callback = MagicMock()
        result = downloader.wait_for_completion("gid123", poll_interval=0.01, progress_callback=callback)
        assert result["status"] == "complete"
        callback.assert_called_once_with(50, 100, 1000)

    @patch("time.sleep")
    def test_callback_called_multiple_times(self, mock_sleep, downloader, mock_aria2):
        mock_aria2.tell_status.side_effect = [
            {"status": "active", "completedLength": "10", "totalLength": "100", "downloadSpeed": "500"},
            {"status": "active", "completedLength": "50", "totalLength": "100", "downloadSpeed": "1000"},
            {"status": "complete"},
        ]
        callback = MagicMock()
        downloader.wait_for_completion("gid123", poll_interval=0.01, progress_callback=callback)
        assert callback.call_count == 2

    @patch("time.sleep")
    def test_zero_total_no_division_error(self, mock_sleep, downloader, mock_aria2):
        mock_aria2.tell_status.side_effect = [
            {"status": "active", "completedLength": "0", "totalLength": "0", "downloadSpeed": "0"},
            {"status": "complete"},
        ]
        callback = MagicMock()
        downloader.wait_for_completion("gid123", poll_interval=0.01, progress_callback=callback)
        # Should not raise ZeroDivisionError
        callback.assert_called_once_with(0, 0, 0)

    @patch("time.sleep")
    def test_empty_fields_default_to_zero(self, mock_sleep, downloader, mock_aria2):
        mock_aria2.tell_status.side_effect = [
            {"status": "active"},
            {"status": "complete"},
        ]
        callback = MagicMock()
        downloader.wait_for_completion("gid123", poll_interval=0.01, progress_callback=callback)
        callback.assert_called_once_with(0, 0, 0)
