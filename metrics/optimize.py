"""Long-only portfolio optimisation without external solvers.

Uses iterated Dirichlet sampling: sample the weight simplex, keep the best
candidate for each objective, then re-sample concentrated around the incumbent
with increasing sharpness. Deterministic (seeded) and fast enough for
interactive use (~vectorised evaluation of thousands of candidates per round).

Not a true QP optimum, but converges well within the display precision the
app needs, and guarantees long-only weights that sum to 1.
"""
import numpy as np

TRADING_DAYS_PER_YEAR = 252


def _evaluate(W, mu, cov, rfr):
    rets = W @ mu
    vols = np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", W, cov, W), 0.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        sharpes = np.where(vols > 0, (rets - rfr) / vols, -np.inf)
    return rets, vols, sharpes


def portfolio_stats(returns, weights_map, rfr=0.0):
    """Annualised return / volatility / Sharpe for a {ticker: weight} map."""
    tickers = list(returns.columns)
    w = np.array([weights_map.get(t, 0.0) for t in tickers], dtype=float)
    total = w.sum()
    if total <= 0:
        return {"ret": np.nan, "vol": np.nan, "sharpe": np.nan}
    w = w / total
    mu = returns.mean().values * TRADING_DAYS_PER_YEAR
    cov = (returns.cov() * TRADING_DAYS_PER_YEAR).values
    ret = float(w @ mu)
    vol = float(np.sqrt(max(w @ cov @ w, 0.0)))
    sharpe = (ret - rfr) / vol if vol > 0 else np.nan
    return {"ret": ret, "vol": vol, "sharpe": sharpe}


def optimize_portfolios(returns, rfr=0.0, n_samples=4000, n_rounds=5, seed=42):
    """Find approximate long-only max-Sharpe and min-volatility portfolios.

    returns : wide DataFrame of daily returns (held tickers only)
    Returns {"max_sharpe": {...}, "min_vol": {...}} where each entry holds
    weights (dict), ret, vol, sharpe (annualised).
    """
    tickers = list(returns.columns)
    k = len(tickers)
    mu = returns.mean().values * TRADING_DAYS_PER_YEAR
    cov = (returns.cov() * TRADING_DAYS_PER_YEAR).values

    if k == 1:
        stats = portfolio_stats(returns, {tickers[0]: 1.0}, rfr)
        entry = {"weights": {tickers[0]: 1.0}, **stats}
        return {"max_sharpe": entry, "min_vol": entry}

    rng = np.random.default_rng(seed)

    # Fixed candidates: equal weight + single-asset vertices
    fixed = np.vstack([np.ones(k) / k, np.eye(k)])

    best = {
        "max_sharpe": {"w": np.ones(k) / k, "score": -np.inf},
        "min_vol": {"w": np.ones(k) / k, "score": -np.inf},
    }

    for round_i in range(n_rounds):
        sharpness = 8.0 * (3.0 ** round_i)
        candidates = [fixed] if round_i == 0 else []
        if round_i == 0:
            candidates.append(rng.dirichlet(np.ones(k), size=n_samples))
        else:
            for key in best:
                alpha = best[key]["w"] * sharpness + 0.05
                candidates.append(rng.dirichlet(alpha, size=n_samples // 2))
        W = np.vstack(candidates)
        rets, vols, sharpes = _evaluate(W, mu, cov, rfr)

        i_s = int(np.nanargmax(sharpes))
        if sharpes[i_s] > best["max_sharpe"]["score"]:
            best["max_sharpe"] = {"w": W[i_s], "score": float(sharpes[i_s])}

        neg_vols = -vols
        i_v = int(np.nanargmax(neg_vols))
        if neg_vols[i_v] > best["min_vol"]["score"]:
            best["min_vol"] = {"w": W[i_v], "score": float(neg_vols[i_v])}

    out = {}
    for key in ("max_sharpe", "min_vol"):
        w = best[key]["w"]
        # zero out dust weights and renormalise for a readable allocation
        w = np.where(w < 0.005, 0.0, w)
        w = w / w.sum()
        ret = float(w @ mu)
        vol = float(np.sqrt(max(w @ cov @ w, 0.0)))
        out[key] = {
            "weights": {t: float(wi) for t, wi in zip(tickers, w)},
            "ret": ret,
            "vol": vol,
            "sharpe": (ret - rfr) / vol if vol > 0 else np.nan,
        }
    return out
