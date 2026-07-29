"""Tests for Dashboard — Rich Live TUI."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from hf_sync.ui.dashboard import Dashboard


class TestDashboard:
    def test_init(self):
        d = Dashboard()
        assert d._live is None

    def test_start_creates_live(self):
        d = Dashboard()
        with patch("hf_sync.ui.dashboard.Live") as mock_live_cls:
            mock_live_instance = MagicMock()
            mock_live_cls.return_value = mock_live_instance
            d.start()
            assert d._live is mock_live_instance
            mock_live_instance.__enter__.assert_called_once()

    def test_stop_exits_live(self):
        d = Dashboard()
        mock_live = MagicMock()
        d._live = mock_live
        d.stop()
        mock_live.__exit__.assert_called_once_with(None, None, None)
        assert d._live is None

    def test_stop_noop_when_not_started(self):
        d = Dashboard()
        d.stop()  # should not crash

    def test_update_noop_without_live(self):
        d = Dashboard()
        d.update("download", "f.bin", 50, 100)  # should not crash

    def test_update_calls_live_update(self):
        d = Dashboard()
        mock_live = MagicMock()
        d._live = mock_live
        d.update("download", "f.bin", 50, 100)
        mock_live.update.assert_called_once()

    def test_build_layout_returns_layout(self):
        d = Dashboard()
        layout = d._build_layout()
        assert layout is not None
