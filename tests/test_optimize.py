"""Tests for metrics/optimize.py against analytic solutions."""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
import pytest

from metrics import optimize


def make_returns(cov_annual, mu_annual, n_days=1500, seed=7):
    """Simulate daily returns with a target annual covariance and mean."""
    rng = np.random.default_rng(seed)
    k = len(mu_annual)
    daily_cov = np.array(cov_annual) / 252
    daily_mu = np.array(mu_annual) / 252
    data = rng.multivariate_normal(daily_mu, daily_cov, size=n_days)
    return pd.DataFrame(data, columns=[f"T{i}" for i in range(k)])


class TestMinVol:
    def test_two_asset_analytic(self):
        # analytic min-vol weight: w1 = (s2^2 - s12) / (s1^2 + s2^2 - 2 s12)
        returns = make_returns(
            cov_annual=[[0.09, 0.0072], [0.0072, 0.04]],  # 30% & 20% vol, corr 0.12
            mu_annual=[0.10, 0.07],
        )
        cov = (returns.cov() * 252).values
        s1, s2, s12 = cov[0, 0], cov[1, 1], cov[0, 1]
        w1_analytic = (s2 - s12) / (s1 + s2 - 2 * s12)

        out = optimize.optimize_portfolios(returns, rfr=0.03)
        w1 = out["min_vol"]["weights"]["T0"]
        assert w1 == pytest.approx(w1_analytic, abs=0.03)

    def test_min_vol_not_above_equal_weight_vol(self):
        returns = make_returns(
            cov_annual=[[0.09, 0.01, 0.02], [0.01, 0.04, 0.005], [0.02, 0.005, 0.0625]],
            mu_annual=[0.10, 0.06, 0.08],
        )
        out = optimize.optimize_portfolios(returns)
        ew_stats = optimize.portfolio_stats(
            returns, {t: 1 / 3 for t in returns.columns}
        )
        assert out["min_vol"]["vol"] <= ew_stats["vol"] + 1e-9


class TestMaxSharpe:
    def test_beats_equal_weight(self):
        returns = make_returns(
            cov_annual=[[0.09, 0.01, 0.02], [0.01, 0.04, 0.005], [0.02, 0.005, 0.0625]],
            mu_annual=[0.12, 0.05, 0.09],
        )
        rfr = 0.03
        out = optimize.optimize_portfolios(returns, rfr=rfr)
        ew = optimize.portfolio_stats(returns, {t: 1 / 3 for t in returns.columns}, rfr)
        assert out["max_sharpe"]["sharpe"] >= ew["sharpe"] - 1e-9

    def test_weights_valid(self):
        returns = make_returns(
            cov_annual=[[0.09, 0.01], [0.01, 0.04]],
            mu_annual=[0.10, 0.07],
        )
        out = optimize.optimize_portfolios(returns)
        for entry in out.values():
            w = np.array(list(entry["weights"].values()))
            assert w.min() >= 0
            assert w.sum() == pytest.approx(1.0)

    def test_single_asset(self):
        returns = make_returns(cov_annual=[[0.04]], mu_annual=[0.08])
        out = optimize.optimize_portfolios(returns)
        assert out["max_sharpe"]["weights"] == {"T0": 1.0}

    def test_deterministic(self):
        returns = make_returns(
            cov_annual=[[0.09, 0.01], [0.01, 0.04]],
            mu_annual=[0.10, 0.07],
        )
        a = optimize.optimize_portfolios(returns)
        b = optimize.optimize_portfolios(returns)
        assert a["max_sharpe"]["weights"] == b["max_sharpe"]["weights"]
