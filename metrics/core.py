# metrics/core.py
import pandas as pd
import numpy as np

TRADING_DAYS_PER_YEAR = 252

#Utility
def _daily_returns(price_df):
    """Pivot price data to wide format and compute daily returns."""
    wide = price_df.pivot(index="date", columns="ticker", values="close")
    returns = wide.pct_change().dropna(how="all")
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
    cov = np.cov(asset_returns, benchmark_returns)[0][1]
    var_bench = np.var(benchmark_returns)
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

#Group metrics
def correlation_matrix(returns):
    return returns.corr()

def portfolio_return_series(returns, weights):
    return (returns * weights).sum(axis=1)

def compute_asset_metrics(price_df, benchmark_ticker, risk_free_rate=0.0):
    returns = _daily_returns(price_df)
    benchmark = returns[benchmark_ticker]
    results = {}
    for ticker in returns.columns:
        r = returns[ticker].dropna()
        results[ticker] = {
            "Sharpe": sharpe_ratio(r, risk_free_rate),
            "Sortino": sortino_ratio(r, risk_free_rate),
            "Beta": beta(r, benchmark) if ticker != benchmark_ticker else np.nan,
            "MaxDrawdown": max_drawdown(r),
            "VaR": var_historical(r),
            "CVaR": cvar_historical(r),
        }
    return pd.DataFrame(results).T

def compute_portfolio_metrics(price_df, weights, benchmark_ticker, risk_free_rate=0.0):
    returns = _daily_returns(price_df)
    port_r = portfolio_return_series(returns, np.array(weights))
    bench_r = returns[benchmark_ticker]
    metrics = {
        "Sharpe": sharpe_ratio(port_r, risk_free_rate),
        "Sortino": sortino_ratio(port_r, risk_free_rate),
        "Beta": beta(port_r, bench_r),
        "MaxDrawdown": max_drawdown(port_r),
        "VaR": var_historical(port_r),
        "CVaR": cvar_historical(port_r),
    }
    corr = correlation_matrix(returns)
    return metrics, corr
