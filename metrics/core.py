# metrics/core.py
import pandas as pd
import numpy as np

TRADING_DAYS_PER_YEAR = 252

#Utility
def _daily_returns(price_df):
    """Pivot price data to wide format and compute daily returns.
    Missing prices are forward-filled explicitly (pandas is deprecating the
    implicit pad inside pct_change)."""
    wide = price_df.pivot(index="date", columns="ticker", values="close")
    returns = wide.ffill().pct_change(fill_method=None).dropna(how="all")
    return returns

#Per-asset metrics
def sharpe_ratio(returns, risk_free_rate=0.0):
    excess = returns - risk_free_rate / TRADING_DAYS_PER_YEAR
    ann_excess_return = excess.mean() * TRADING_DAYS_PER_YEAR
    ann_std = returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    return ann_excess_return / ann_std

def sortino_ratio(returns, risk_free_rate=0.0):
    excess = returns - risk_free_rate / TRADING_DAYS_PER_YEAR
    downside_std = returns[returns < 0].std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    ann_excess_return = excess.mean() * TRADING_DAYS_PER_YEAR
    return ann_excess_return / downside_std

def beta(asset_returns, benchmark_returns):
    # ddof=1 on both so covariance and variance use the same estimator
    cov = np.cov(asset_returns, benchmark_returns, ddof=1)[0][1]
    var_bench = np.var(benchmark_returns, ddof=1)
    return cov / var_bench

def max_drawdown(returns):
    cum = (1 + returns).cumprod()
    peak = cum.cummax()
    drawdown = (cum - peak) / peak
    return drawdown.min()

def var_historical(returns, level=0.05):
    return np.percentile(returns, 100 * level)

def cvar_historical(returns, level=0.05):
    var = var_historical(returns, level)
    return returns[returns <= var].mean()

def annualized_return(returns):
    return returns.mean() * TRADING_DAYS_PER_YEAR

def annualized_volatility(returns):
    return returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)

#Group metrics
def correlation_matrix(returns):
    return returns.corr()

def _align_weights(returns, weights):
    """Accept a {ticker: weight} dict or a positional array; return array
    aligned to returns.columns so column order can never silently mismatch."""
    if isinstance(weights, dict):
        return np.array([weights.get(t, 0.0) for t in returns.columns])
    return np.asarray(weights, dtype=float)

def portfolio_return_series(returns, weights):
    w = _align_weights(returns, weights)
    return (returns * w).sum(axis=1)

def effective_holdings(weights):
    """Effective number of independent positions: 1 / sum(w^2).
    Equal-weight n assets -> n; one dominant position -> close to 1."""
    w = np.asarray([v for v in weights if v > 0], dtype=float)
    if w.size == 0 or w.sum() == 0:
        return 0.0
    w = w / w.sum()
    return float(1.0 / (w ** 2).sum())

def diversification_score(corr, weights_map):
    """0-100 score combining weighted average pairwise correlation with the
    effective number of holdings. Calibrated so realistic portfolios spread
    across the scale: an all-tech basket lands low, a broad equity mix lands
    mid, and an equity+bond+gold mix lands high.
    """
    held = [t for t, w in weights_map.items() if w > 0 and t in corr.columns]
    if len(held) < 2:
        return 0.0
    sub = corr.loc[held, held].values
    w = np.array([weights_map[t] for t in held], dtype=float)
    w = w / w.sum()
    pair_w = np.outer(w, w)
    mask = ~np.eye(len(held), dtype=bool)
    denom = pair_w[mask].sum()
    avg_corr = float((pair_w[mask] * sub[mask]).sum() / denom) if denom > 0 else 1.0
    # 0.8+ avg correlation -> no diversification benefit; 0 or below -> full marks
    corr_component = float(np.clip((0.8 - avg_corr) / 0.8, 0.0, 1.0))
    n_eff = effective_holdings(w)
    count_component = 1.0 - 1.0 / n_eff if n_eff > 0 else 0.0
    return round(100.0 * corr_component * count_component)

def compute_asset_metrics(price_df, benchmark_ticker, risk_free_rate=0.0):
    returns = _daily_returns(price_df)
    benchmark = returns[benchmark_ticker]
    results = {}
    for ticker in returns.columns:
        r = returns[ticker].dropna()
        if ticker != benchmark_ticker:
            aligned = pd.concat([r, benchmark], axis=1).dropna()
            b = beta(aligned.iloc[:, 0], aligned.iloc[:, 1])
        else:
            b = np.nan
        results[ticker] = {
            "Sharpe": sharpe_ratio(r.dropna(), risk_free_rate),
            "Sortino": sortino_ratio(r.dropna(), risk_free_rate),
            "Beta": b,
            "MaxDrawdown": max_drawdown(r.dropna()),
            "VaR": var_historical(r.dropna()),
            "CVaR": cvar_historical(r.dropna()),
        }
    return pd.DataFrame(results).T

def compute_portfolio_metrics(price_df, weights, benchmark_ticker, risk_free_rate=0.0):
    returns = _daily_returns(price_df)
    port_r = portfolio_return_series(returns, weights)
    bench_r = returns[benchmark_ticker]
    aligned = pd.concat([port_r, bench_r], axis=1).dropna()
    metrics = {
        "Sharpe": sharpe_ratio(port_r.dropna(), risk_free_rate),
        "Sortino": sortino_ratio(port_r.dropna(), risk_free_rate),
        "Beta": beta(aligned.iloc[:, 0], aligned.iloc[:, 1]),
        "MaxDrawdown": max_drawdown(port_r.dropna()),
        "VaR": var_historical(port_r.dropna()),
        "CVaR": cvar_historical(port_r.dropna()),
    }
    corr = correlation_matrix(returns)
    return metrics, corr
