import sqlite3
import pandas as pd

DB_PATH = "data/portfolio_data.db"

def store_prices(df):
    """
    Store daily price data in the daily_prices table.
    Expects a DataFrame with columns: date, open, high, low, close, volume, ticker.
    """
    if df.empty:
        print("[INFO] No price data to store.")
        return
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("daily_prices", conn, if_exists="append", index=False)
    conn.close()
    print(f"[INFO] Stored {len(df)} price rows for {df['ticker'].iloc[0]}")

def store_metadata(meta):
    """
    Store ticker metadata in the tickers_meta table.
    Expects a dict with keys: ticker, name, sector.
    """
    if not meta or not meta.get("ticker"):
        print("[INFO] No metadata to store.")
        return
    conn = sqlite3.connect(DB_PATH)
    df = pd.DataFrame([meta])
    df.to_sql("tickers_meta", conn, if_exists="append", index=False)
    conn.close()
    print(f"[INFO] Stored metadata for {meta['ticker']}")