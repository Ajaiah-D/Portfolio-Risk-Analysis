"""Tests for the cross-checks in scripts/checks.py.

Both checks only use data the pipeline already has: the twin-fund check
compares funds that track the same index, and the adjustment check compares
stored adjusted returns with Yahoo's own raw closes and dividend records.
Synthetic data only; no network.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
import pytest

from scripts import checks, symbols

DAYS = pd.bdate_range("2026-09-01", periods=30)


def returns_frame(members, base=0.002, seed=0, noise=0.0):
    """Daily returns for `members`: one shared move per day plus optional noise."""
    rng = np.random.default_rng(seed)
    common = rng.normal(0, 0.005, len(DAYS)) + base
    data = {m: common + rng.normal(0, noise, len(DAYS)) for m in members}
    return pd.DataFrame(data, index=DAYS)


def closes_from_returns(returns):
    return 100 * (1 + returns).cumprod()


# ── Twin-fund check ───────────────────────────────────────────────────────────
class TestTwinFlags:
    GROUP = {"test": {"members": ["A", "B", "C", "D", "E"], "tolerance": 0.0015}}

    def test_identical_twins_raise_nothing(self):
        r = returns_frame(["A", "B", "C", "D", "E"])
        assert checks.twin_flags(closes_from_returns(r), self.GROUP) == []

    def test_small_tracking_noise_is_tolerated(self):
        r = returns_frame(["A", "B", "C", "D", "E"], noise=0.0002)
        assert checks.twin_flags(closes_from_returns(r), self.GROUP) == []

    def test_missed_dividend_is_flagged_and_does_not_reverse(self):
        # One fund's adjusted series skips a 0.3% dividend: its ex-date return
        # is 0.3% too low and the gap never closes.
        r = returns_frame(["A", "B", "C", "D", "E"])
        r.loc[DAYS[10], "C"] -= 0.003
        flags = checks.twin_flags(closes_from_returns(r), self.GROUP)
        assert [(f["group"], f["date"], f["ticker"]) for f in flags] == [
            ("test", DAYS[10].date().isoformat(), "C")]
        assert flags[0]["deviation"] == pytest.approx(-0.003, abs=1e-9)
        assert flags[0]["reverses"] is False

    def test_stale_price_is_flagged_as_reversing(self):
        # Yahoo repeats a fund's previous NAV, then catches up the next day.
        r = returns_frame(["A", "B", "C", "D", "E"])
        r.loc[DAYS[10]] = 0.01                          # a clear up day...
        r.loc[DAYS[10], "D"] = 0.0                      # ...that D's price missed
        r.loc[DAYS[11], "D"] = 1.01 * (1 + r.loc[DAYS[11], "A"]) - 1
        flags = checks.twin_flags(closes_from_returns(r), self.GROUP)
        first = [f for f in flags if f["date"] == DAYS[10].date().isoformat()]
        assert [f["ticker"] for f in first] == ["D"]
        assert first[0]["reverses"] is True
        assert first[0]["undoes_previous"] is False
        # The catch-up day is flagged too, but marked as undoing the gap
        # rather than looking like a new, persistent one.
        second = [f for f in flags if f["date"] == DAYS[11].date().isoformat()]
        assert [f["ticker"] for f in second] == ["D"]
        assert second[0]["undoes_previous"] is True

    def test_latest_day_cannot_be_called_a_reversal(self):
        r = returns_frame(["A", "B", "C", "D", "E"])
        r.loc[DAYS[-1], "B"] -= 0.004
        flags = checks.twin_flags(closes_from_returns(r), self.GROUP)
        assert [(f["date"], f["ticker"]) for f in flags] == [(DAYS[-1].date().isoformat(), "B")]
        assert flags[0]["reverses"] is None

    def test_tolerance_widens_on_big_market_days(self):
        # ETF closing prints and fund NAVs drift apart more on big days, so a
        # 0.4% gap is noise on a 10% day but a finding on a 0.5% day.
        r = returns_frame(["A", "B", "C", "D", "E"])
        r.loc[DAYS[5]] = 0.10
        r.loc[DAYS[5], "A"] = 0.104
        r.loc[DAYS[15]] = 0.005
        r.loc[DAYS[15], "A"] = 0.009
        flags = checks.twin_flags(closes_from_returns(r), self.GROUP)
        assert [f["date"] for f in flags] == [DAYS[15].date().isoformat()]

    def test_members_missing_from_the_data_are_ignored(self):
        r = returns_frame(["A", "B", "C"])
        assert checks.twin_flags(closes_from_returns(r), self.GROUP) == []

    def test_a_group_with_one_member_present_is_skipped(self):
        r = returns_frame(["A"])
        r.loc[DAYS[3], "A"] += 0.05
        assert checks.twin_flags(closes_from_returns(r), self.GROUP) == []

    def test_a_missing_day_is_skipped_not_compared_across_the_gap(self):
        closes = closes_from_returns(returns_frame(["A", "B", "C", "D", "E"]))
        closes.loc[DAYS[8], "E"] = np.nan
        closes.loc[DAYS[9]:, "E"] *= 1.01
        assert checks.twin_flags(closes, self.GROUP) == []

    def test_pair_flags_both_members_at_half_the_gap(self):
        group = {"pair": {"members": ["A", "B"], "tolerance": 0.001}}
        r = returns_frame(["A", "B"])
        r.loc[DAYS[7], "A"] -= 0.003
        flags = checks.twin_flags(closes_from_returns(r), group)
        assert sorted(f["ticker"] for f in flags) == ["A", "B"]
        assert all(abs(f["deviation"]) == pytest.approx(0.0015, abs=1e-9) for f in flags)


class TestTwinGroupDefinitions:
    """The real groups: each must catch the distribution size it was
    calibrated for (see the README), and only list real tickers."""

    @pytest.mark.parametrize("name", list(checks.TWIN_GROUPS))
    def test_group_catches_its_target_distribution_on_a_quiet_day(self, name):
        spec = checks.TWIN_GROUPS[name]
        members = spec["members"]
        r = returns_frame(members, base=0.0)
        r.loc[DAYS[10]] = 0.002
        r.loc[DAYS[10], members[0]] -= spec["catches"]
        flags = checks.twin_flags(closes_from_returns(r), {name: spec})
        assert members[0] in [f["ticker"] for f in flags if f["date"] == DAYS[10].date().isoformat()]

    @pytest.mark.parametrize("name", list(checks.TWIN_GROUPS))
    def test_every_group_documents_why_its_members_are_twins(self, name):
        spec = checks.TWIN_GROUPS[name]
        assert len(spec["members"]) >= 2
        assert spec["why"].strip()
        assert 0 < spec["tolerance"] < spec["catches"]

    def test_no_ticker_is_in_two_groups(self):
        members = [m for spec in checks.TWIN_GROUPS.values() for m in spec["members"]]
        assert len(members) == len(set(members))

    def test_every_mutual_fund_has_a_twin_group(self):
        # A fund is only added if it can be checked against its twins.
        grouped = {m for spec in checks.TWIN_GROUPS.values() for m in spec["members"]}
        funds = symbols.load_mutual_funds()
        assert funds, "tickers/mutual_funds.csv should list the funds"
        assert set(funds) <= grouped


# ── Adjustment check ──────────────────────────────────────────────────────────
def yahoo_frame(raw_closes, dividends=None, splits=None):
    """A frame shaped like fetch_yf's output: `close` is adjusted the way
    Yahoo does it (each dividend scales every earlier close by
    1 - dividend / previous raw close), and the raw evidence is kept."""
    raw = np.asarray(raw_closes, dtype=float)
    div = np.zeros(len(raw)) if dividends is None else np.asarray(dividends, dtype=float)
    factor = np.ones(len(raw))
    for i in range(len(raw) - 1, 0, -1):
        factor[:i] *= 1 - div[i] / raw[i - 1]
    return pd.DataFrame({
        "date": [d.date() for d in DAYS[:len(raw)]],
        "close": raw * factor,
        "close_raw": raw,
        "dividend": div,
        "split": np.zeros(len(raw)) if splits is None else np.asarray(splits, dtype=float),
    })


class TestAdjustmentMismatches:
    def test_correct_dividend_adjustment_passes(self):
        df = yahoo_frame([100, 101, 99.5, 100], dividends=[0, 0, 1.0, 0])
        assert checks.adjustment_mismatches(df) == []

    def test_stored_return_that_skips_the_dividend_is_caught(self):
        df = yahoo_frame([100, 101, 99.5, 100], dividends=[0, 0, 1.0, 0])
        df["close"] = df["close_raw"]              # adjustment never applied
        found = checks.adjustment_mismatches(df)
        assert [m["date"] for m in found] == [df["date"][2].isoformat()]
        assert found[0]["stored"] == pytest.approx(99.5 / 101 - 1)
        assert found[0]["implied"] == pytest.approx(99.5 / 100 - 1)

    def test_wrong_dividend_amount_in_the_adjustment_is_caught(self):
        df = yahoo_frame([100, 101, 99.5, 100], dividends=[0, 0, 1.0, 0])
        df["dividend"] = [0, 0, 0.5, 0]            # record disagrees with adjustment
        assert len(checks.adjustment_mismatches(df)) == 1

    def test_split_that_the_stored_series_missed_is_caught(self):
        # Yahoo's raw close is already split-adjusted; a stored series that
        # was not adjusted shows a -90% day where the raw closes show none.
        df = yahoo_frame([10, 10.2, 10.1, 10.3], splits=[0, 0, 10, 0])
        df["close"] = [100, 102, 10.1, 10.3]
        found = checks.adjustment_mismatches(df)
        assert [m["date"] for m in found] == [df["date"][2].isoformat()]
        assert found[0]["split"] == 10

    def test_correct_split_passes(self):
        df = yahoo_frame([10, 10.2, 10.1, 10.3], splits=[0, 0, 10, 0])
        assert checks.adjustment_mismatches(df) == []

    def test_days_without_a_dividend_or_split_are_not_checked(self):
        df = yahoo_frame([100, 101, 102, 103])
        df.loc[2, "close"] = 150                   # a bad day, but not this check's job
        assert checks.adjustment_mismatches(df) == []

    def test_event_on_the_first_row_has_nothing_to_compare(self):
        df = yahoo_frame([100, 101], dividends=[1.0, 0])
        assert checks.adjustment_mismatches(df) == []

    def test_mutual_fund_capital_gain_counts_as_a_distribution(self):
        # fetch_yf folds capital gains into `dividend`; a 3% distribution.
        df = yahoo_frame([20, 20.1, 19.5, 19.6], dividends=[0, 0, 0.6, 0])
        assert checks.adjustment_mismatches(df) == []

    def test_frame_without_raw_columns_is_skipped(self):
        df = pd.DataFrame({"date": [d.date() for d in DAYS[:3]], "close": [1.0, 2.0, 3.0]})
        assert checks.adjustment_mismatches(df) == []

    def test_float_noise_is_not_a_mismatch(self):
        df = yahoo_frame([100, 101, 99.5, 100], dividends=[0, 0, 1.0, 0])
        df["close"] *= 1 + np.array([0, 1e-7, -1e-7, 0])
        assert checks.adjustment_mismatches(df) == []


# ── GitHub annotations ────────────────────────────────────────────────────────
class TestAnnotations:
    def test_prints_a_warning_annotation_in_actions(self, monkeypatch, capsys):
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        checks.annotate_warning("Twin-fund check", "VFIAX 2025-06-24 off by 1.1%")
        assert capsys.readouterr().out == "::warning title=Twin-fund check::VFIAX 2025-06-24 off by 1.1%\n"

    def test_silent_outside_actions(self, monkeypatch, capsys):
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        checks.annotate_warning("t", "m")
        assert capsys.readouterr().out == ""
