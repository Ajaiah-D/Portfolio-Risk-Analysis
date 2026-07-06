"""Unit tests for metrics/core.py — hand-checked values on small fixtures."""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
import pytest

from metrics import core


@pytest.fixture
def simple_returns():
    return pd.Series([0.01, -0.02, 0.015, 0.005, -0.01])


def make_price_df():
    """3 tickers, 6 days, deterministic prices."""
    dates = pd.date_range("2024-01-01", periods=6, freq="B")
    rows = []
    prices = {
        "AAA": [100, 101, 99, 102, 103, 104],
        "BBB": [50, 50.5, 49.9, 50.8, 51.0, 51.5],
        "SPY": [400, 402, 398, 404, 406, 408],
    }
    for ticker, series in prices.items():
        for d, p in zip(dates, series):
            rows.append({"date": d, "ticker": ticker, "close": p})
    return pd.DataFrame(rows)


class TestSharpe:
    def test_zero_rfr(self, simple_returns):
        r = simple_returns
        expected = (r.mean() * 252) / (r.std() * np.sqrt(252))
        assert core.sharpe_ratio(r) == pytest.approx(expected)

    def test_rfr_reduces_sharpe(self, simple_returns):
        assert core.sharpe_ratio(simple_returns, 0.05) < core.sharpe_ratio(simple_returns, 0.0)


class TestSortino:
    def test_uses_downside_std_only(self, simple_returns):
        r = simple_returns
        downside = r[r < 0].std() * np.sqrt(252)
        expected = (r.mean() * 252) / downside
        assert core.sortino_ratio(r) == pytest.approx(expected)


class TestBeta:
    def test_beta_of_self_is_one(self):
        rng = np.random.default_rng(1)
        r = pd.Series(rng.normal(0, 0.01, 100))
        assert core.beta(r, r) == pytest.approx(1.0)

    def test_beta_of_scaled_series(self):
        rng = np.random.default_rng(2)
        bench = pd.Series(rng.normal(0, 0.01, 200))
        asset = bench * 1.5
        assert core.beta(asset, bench) == pytest.approx(1.5)

    def test_consistent_ddof(self):
        # cov(ddof=1)/var(ddof=1) — a 2x-beta asset must give exactly 2.0
        # regardless of sample size (the old ddof mismatch broke this)
        bench = pd.Series([0.01, -0.01, 0.02, -0.02, 0.005])
        asset = bench * 2
        assert core.beta(asset, bench) == pytest.approx(2.0)


class TestDrawdown:
    def test_known_drawdown(self):
        # 100 -> 110 -> 88 : drawdown = (88 - 110) / 110 = -0.2
        r = pd.Series([0.10, -0.20])
        assert core.max_drawdown(r) == pytest.approx(-0.20)

    def test_monotonic_up_has_zero_drawdown(self):
        r = pd.Series([0.01, 0.02, 0.005])
        assert core.max_drawdown(r) == pytest.approx(0.0)


class TestVaR:
    def test_var_is_5th_percentile(self):
        r = pd.Series(np.arange(-0.05, 0.05, 0.001))
        assert core.var_historical(r) == pytest.approx(np.percentile(r, 5))

    def test_cvar_below_var(self):
        rng = np.random.default_rng(3)
        r = pd.Series(rng.normal(0, 0.02, 500))
        assert core.cvar_historical(r) <= core.var_historical(r)


class TestWeights:
    def test_dict_weights_align_to_columns(self):
        df = make_price_df()
        returns = core._daily_returns(df)
        # dict order deliberately scrambled vs. column order
        w = {"SPY": 0.0, "BBB": 0.5, "AAA": 0.5}
        series = core.portfolio_return_series(returns, w)
        manual = 0.5 * returns["AAA"] + 0.5 * returns["BBB"]
        pd.testing.assert_series_equal(series, manual, check_names=False)

    def test_effective_holdings(self):
        assert core.effective_holdings([0.25, 0.25, 0.25, 0.25]) == pytest.approx(4.0)
        assert core.effective_holdings([1.0]) == pytest.approx(1.0)
        # dominant position collapses toward 1
        assert core.effective_holdings([0.97, 0.01, 0.01, 0.01]) < 1.1


class TestDiversificationScore:
    def _corr(self, vals, names):
        return pd.DataFrame(vals, index=names, columns=names)

    def test_perfectly_correlated_scores_zero(self):
        corr = self._corr(np.ones((3, 3)), ["A", "B", "C"])
        w = {"A": 1 / 3, "B": 1 / 3, "C": 1 / 3}
        assert core.diversification_score(corr, w) == 0

    def test_uncorrelated_many_holdings_scores_high(self):
        n = 10
        names = [f"T{i}" for i in range(n)]
        corr = self._corr(np.eye(n), names)
        w = {t: 1 / n for t in names}
        assert core.diversification_score(corr, w) >= 85

    def test_single_holding_scores_zero(self):
        corr = self._corr(np.eye(2), ["A", "B"])
        assert core.diversification_score(corr, {"A": 1.0}) == 0

    def test_typical_equity_mix_lands_midrange(self):
        # 8 holdings, avg pairwise corr ~0.45 — should be mid-scale, not bottom
        n = 8
        names = [f"T{i}" for i in range(n)]
        vals = np.full((n, n), 0.45)
        np.fill_diagonal(vals, 1.0)
        corr = self._corr(vals, names)
        w = {t: 1 / n for t in names}
        score = core.diversification_score(corr, w)
        assert 25 <= score <= 55

    def test_zero_weight_tickers_ignored(self):
        corr = self._corr(np.eye(3), ["A", "B", "SPY"])
        w = {"A": 0.5, "B": 0.5, "SPY": 0.0}
        w2 = {"A": 0.5, "B": 0.5}
        assert core.diversification_score(corr, w) == core.diversification_score(corr, w2)


class TestPipelines:
    def test_compute_asset_metrics_shape(self):
        df = make_price_df()
        out = core.compute_asset_metrics(df, benchmark_ticker="SPY")
        assert set(out.index) == {"AAA", "BBB", "SPY"}
        assert np.isnan(out.loc["SPY", "Beta"])

    def test_compute_portfolio_metrics_dict_weights(self):
        df = make_price_df()
        metrics, corr = core.compute_portfolio_metrics(
            df, {"AAA": 0.5, "BBB": 0.5, "SPY": 0.0}, benchmark_ticker="SPY"
        )
        assert set(metrics) == {"Sharpe", "Sortino", "Beta", "MaxDrawdown", "VaR", "CVaR"}
        assert corr.shape == (3, 3)
