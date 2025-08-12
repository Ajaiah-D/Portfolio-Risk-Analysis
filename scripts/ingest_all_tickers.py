import pandas as pd
from scripts.fetch_data import fetch_prices, fetch_ticker_metadata
from scripts.store_data import store_prices, store_metadata

def log_info(msg):
    """Simple logger for scripts."""
    print(f"[INFO] {msg}")

ETF_LIST = [
    # Broad US
    "SPY", "IVV", "VOO", "VTI", "DIA", "QQQ", "IWM",
    # Real assets
    "VNQ", "GLD", "SLV", "DBC",
    # Sector SPDRs
    "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLB", "XLRE", "XLC",
    # International
    "EFA", "VEA", "EEM", "VWO"
]

def ingest_all_tickers():
    # df = pd.read_csv("tickers/constituents.csv")
    # tickers = df["Symbol"].unique()
    tickers = ETF_LIST
    end_date = "2025-07-18"
    start_date = "2015-07-18"
    failed_tickers = []

    for ticker in tickers:
        try:
            prices = fetch_prices(ticker, start_date, end_date)
            meta = fetch_ticker_metadata(ticker)
            if prices.empty or not meta:
                log_info(f"Skipping {ticker} due to missing data.")
                failed_tickers.append(ticker)
                continue
            store_prices(prices)
            store_metadata(meta)
        except Exception as e:
            log_info(f"Error processing {ticker}: {e}")
            failed_tickers.append(ticker)
            continue

    if failed_tickers:
        print("Failed tickers:", failed_tickers)
        with open("data/failed_tickers.txt", "w") as f:
            for t in failed_tickers:
                f.write(f"{t}\n")

if __name__ == "__main__":
    ingest_all_tickers()
    