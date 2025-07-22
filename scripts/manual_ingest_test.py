import pandas as pd
from scripts.utils import get_api_key, log_info, handle_rate_limit
from scripts.fetch_data import fetch_prices, fetch_ticker_metadata
from scripts.store_data import store_prices, store_metadata

df = pd.read_csv("tickers/constituents.csv")
tickers = df["Symbol"].unique()
end_date = "2025-07-18"
start_date = "2015-07-18"

for ticker in tickers[:5]:  # Try first 5 tickers for a quick test
    prices = fetch_prices(ticker, start_date, end_date)
    meta = fetch_ticker_metadata(ticker)
    store_prices(prices)
    store_metadata(meta)