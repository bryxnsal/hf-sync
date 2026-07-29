"""Tests for UI components: ProgressTracker, render_table, Dashboard."""

from __future__ import annotations

from hf_sync.ui.progress import ProgressTracker
from hf_sync.ui.tables import render_table


# --- ProgressTracker ---

class TestProgressTracker:
    def test_init_resets(self) -> None:
        t = ProgressTracker()
        assert t.current == 0
        assert t.total == 0
        assert t.stage == ""

    def test_reset(self) -> None:
        t = ProgressTracker()
        t.current = 5
        t.total = 10
        t.stage = "download"
        t.reset()
        assert t.current == 0
        assert t.total == 0
        assert t.stage == ""

    def test_update_increments(self) -> None:
        t = ProgressTracker()
        t.update()
        assert t.current == 1

    def test_update_n(self) -> None:
        t = ProgressTracker()
        t.update(5)
        assert t.current == 5

    def test_update_chained(self) -> None:
        t = ProgressTracker()
        t.update(3)
        t.update(2)
        assert t.current == 5


# --- render_table ---

class TestRenderTable:
    def test_basic_table(self) -> None:
        out = render_table(
            title="Test",
            headers=["Name", "Value"],
            rows=[["a", "1"], ["b", "2"]],
        )
        assert "Test" in out
        assert "Name" in out
        assert "Value" in out
        assert "a" in out

    def test_empty_rows(self) -> None:
        out = render_table(title="Empty", headers=["Col"], rows=[])
        assert "Empty" in out
        assert "Col" in out

    def test_single_row(self) -> None:
        out = render_table(title="Single", headers=["X"], rows=[["hello"]])
        assert "hello" in out
