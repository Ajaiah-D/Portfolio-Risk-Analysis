"""Tests for the budget-constrained allocation logic (custom weighting)."""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from streamlit_app import allocation


PICKS = ["A", "B", "C", "D"]


class TestSpread:
    def test_equal_split_when_nothing_locked(self):
        out = allocation.spread(5.0, [], {}, PICKS)
        assert out == {"A": 1.25, "B": 1.25, "C": 1.25, "D": 1.25}
        assert sum(out.values()) == pytest.approx(5.0)

    def test_locked_amounts_preserved_remainder_split(self):
        # the user's example: $5 budget, 4 stocks, one set to $2 -> others $1
        out = allocation.spread(5.0, ["A"], {"A": 2.0}, PICKS)
        assert out["A"] == 2.0
        assert out["B"] == out["C"] == out["D"] == 1.0

    def test_rounding_drift_absorbed_total_exact(self):
        out = allocation.spread(100.0, [], {}, ["A", "B", "C"])
        assert sum(out.values()) == pytest.approx(100.0, abs=0.001)

    def test_all_locked_returns_unchanged(self):
        amounts = {"A": 1.0, "B": 2.0, "C": 3.0, "D": 4.0}
        out = allocation.spread(5.0, PICKS, amounts, PICKS)
        assert out == amounts

    def test_locked_over_budget_gives_zero_to_free(self):
        out = allocation.spread(5.0, ["A"], {"A": 5.0}, PICKS)
        assert out["A"] == 5.0
        assert out["B"] == out["C"] == out["D"] == 0.0


class TestApplyEdit:
    def test_simple_edit_rebalances_others(self):
        start = allocation.spread(5.0, [], {}, PICKS)
        ok, amounts, locked, over = allocation.apply_edit(
            5.0, [], start, PICKS, {"A": 2.0}
        )
        assert ok
        assert amounts["A"] == 2.0
        assert amounts["B"] == amounts["C"] == amounts["D"] == 1.0
        assert locked == ["A"]
        assert over == 0.0

    def test_second_edit_keeps_first_lock(self):
        ok, amounts, locked, _ = allocation.apply_edit(
            10.0, ["A"], {"A": 4.0, "B": 2.0, "C": 2.0, "D": 2.0}, PICKS, {"B": 3.0}
        )
        assert ok
        assert amounts["A"] == 4.0        # first edit untouched
        assert amounts["B"] == 3.0        # second edit applied
        assert amounts["C"] == amounts["D"] == 1.5  # remainder split
        assert set(locked) == {"A", "B"}

    def test_over_budget_rejected_unchanged(self):
        start = allocation.spread(5.0, [], {}, PICKS)
        ok, amounts, locked, over = allocation.apply_edit(
            5.0, [], start, PICKS, {"A": 6.0}
        )
        assert not ok
        assert amounts == start           # nothing applied
        assert locked == []
        assert over == pytest.approx(1.0)

    def test_edit_exactly_at_budget_allowed(self):
        start = allocation.spread(5.0, [], {}, PICKS)
        ok, amounts, _, _ = allocation.apply_edit(5.0, [], start, PICKS, {"A": 5.0})
        assert ok
        assert amounts["A"] == 5.0
        assert amounts["B"] == amounts["C"] == amounts["D"] == 0.0

    def test_locked_sum_over_budget_rejected(self):
        ok, _, _, over = allocation.apply_edit(
            10.0, ["A", "B"], {"A": 5.0, "B": 4.0, "C": 0.5, "D": 0.5},
            PICKS, {"C": 2.0}
        )
        assert not ok
        assert over == pytest.approx(1.0)

    def test_removed_ticker_dropped_from_locks(self):
        ok, amounts, locked, _ = allocation.apply_edit(
            6.0, ["Z"], {"A": 2.0, "B": 2.0, "C": 2.0}, ["A", "B", "C"], {"A": 3.0}
        )
        assert ok
        assert "Z" not in locked and "Z" not in amounts
        assert amounts["A"] == 3.0
        assert amounts["B"] == amounts["C"] == 1.5


class TestTotalMismatch:
    def test_zero_when_free_tickers_remain(self):
        assert allocation.total_mismatch(5.0, ["A"], {"A": 9.0}, PICKS) == 0.0

    def test_reports_diff_when_all_locked(self):
        amounts = {"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0}
        assert allocation.total_mismatch(5.0, PICKS, amounts, PICKS) == pytest.approx(-1.0)

    def test_zero_when_all_locked_but_matching(self):
        amounts = {"A": 1.25, "B": 1.25, "C": 1.25, "D": 1.25}
        assert allocation.total_mismatch(5.0, PICKS, amounts, PICKS) == 0.0
