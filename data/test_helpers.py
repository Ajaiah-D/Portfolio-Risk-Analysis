import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from metrics import core
import helpers
import numpy as np

tickers = ["AAPL", "MSFT", "SPY"]
start = "2022-01-01"
end = "2024-07-18"
benchmark = "SPY"
risk_free = 0.0
weights = [0.4, 0.4, 0.2]  # Example weights, must sum to 1 and match tickers order

# 1. Get price data
df = helpers.get_price_data(tickers, start, end)
print("Sample price data:")
print(df.head())

# 2. Compute asset metrics
asset_df = core.compute_asset_metrics(df, benchmark_ticker=benchmark, risk_free_rate=risk_free)
print("\nAsset metrics:")
print(asset_df)

# 3. Compute portfolio metrics
port_dict, corr = core.compute_portfolio_metrics(df, weights, benchmark_ticker=benchmark, risk_free_rate=risk_free)
print("\nPortfolio metrics:")
print(port_dict)

print("\nCorrelation matrix:")
print(corr)