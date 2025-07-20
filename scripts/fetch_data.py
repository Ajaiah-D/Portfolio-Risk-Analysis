import os
import requests
import pandas as pd
from datetime import datetime, date, timedelta
from scripts.utils import get_api_key, log_info, handle_rate_limit

POLYGON_BASE_URL = "https://api.polygon.io"

def fetch_prices(ticker, start_date, end_date):
    """
    Fetch daily OHLCV price data for a ticker from Polygon.io.
    Returns a pandas DataFrame with columns: date, open, high, low, close, volume, ticker.
    """
    api_key = get_api_key()
    url = f"{POLYGON_BASE_URL}/v2/aggs/ticker/{ticker}/range/1/day/{start_date}/{end_date}"
    params = {
        "adjusted": "true",
        "sort": "asc",
        "limit": 50000,
        "apiKey": api_key
    }
    log_info(f"Fetching prices for {ticker} from {start_date} to {end_date}")
    handle_rate_limit()  # Ensures we don't exceed Polygon's free tier rate limit

    response = requests.get(url, params=params)
    if response.status_code != 200:
        log_info(f"Failed to fetch data for {ticker}: {response.status_code} {response.text}")
        return pd.DataFrame()  # Return empty DataFrame on failure

    data = response.json()
    if "results" not in data or not data["results"]:
        log_info(f"No price data found for {ticker}")
        return pd.DataFrame()

    df = pd.DataFrame(data["results"])
    df["date"] = pd.to_datetime(df["t"], unit="ms").dt.date
    df = df.rename(columns={
        "o": "open",
        "h": "high",
        "l": "low",
        "c": "close",
        "v": "volume"
    })
    df["ticker"] = ticker
    return df[["date", "open", "high", "low", "close", "volume", "ticker"]]



def fetch_ticker_metadata(ticker):
    """
    Fetch ticker metadata (name, sector, etc.) from Polygon.io.
    Returns a dict with keys: ticker, name, sector.
    """
    api_key = get_api_key()
    url = f"{POLYGON_BASE_URL}/v3/reference/tickers/{ticker}"
    params = {"apiKey": api_key}
    log_info(f"Fetching metadata for {ticker}")
    handle_rate_limit()
    response = requests.get(url, params=params)
    if response.status_code != 200:
        log_info(f"Failed to fetch metadata for {ticker}: {response.status_code} {response.text}")
        return {}
    data = response.json()
    if "results" not in data:
        log_info(f"No metadata found for {ticker}")
        return {}
    results = data["results"]
    return {
        "ticker": results.get("ticker"),
        "name": results.get("name"),
        "sector": results.get("sic_description")  # sector info is often under 'sic_description'
    }


if __name__ == "__main__":
    ticker = "AAPL"
    end_date = "2025-07-18"
    start_date = (date(2025, 7, 18) - timedelta(days=365*10)).strftime("%Y-%m-%d")
    df = fetch_prices(ticker, start_date, end_date)
    print(df.head())
    print(f"Fetched {len(df)} rows for {ticker}")

    meta = fetch_ticker_metadata(ticker)
    print(meta)