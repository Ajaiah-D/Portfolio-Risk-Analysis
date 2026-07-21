import sqlite3
import pandas as pd

DB_PATH = "data/portfolio_data.db"

def store_prices(df):
    """
    Store daily price data in the daily_prices table.
    Expects a DataFrame with columns: date, open, high, low, close, volume, ticker.
    Uses INSERT OR IGNORE against the (ticker, date) unique index, so this is
    safe to call again for a ticker that's already partially stored.
    """
    if df.empty:
        print("[INFO] No price data to store.")
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    rows = [
        (str(r["date"]), r["open"], r["high"], r["low"], r["close"], r["volume"], r["ticker"])
        for _, r in df.iterrows()
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO daily_prices "
        "(date, open, high, low, close, volume, ticker) VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    print(f"[INFO] Stored {cur.rowcount} new price rows for {df['ticker'].iloc[0]}")

def store_metadata(meta):
    """
    Store ticker metadata in the tickers_meta table.
    Expects a dict with keys: ticker, name, sector.
    Uses INSERT OR IGNORE against a unique index on ticker, so re-running for
    a ticker that already has metadata is a no-op rather than a duplicate row.
    """
    if not meta or not meta.get("ticker"):
        print("[INFO] No metadata to store.")
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_meta_ticker ON tickers_meta (ticker)")
    cur.execute(
        "INSERT OR IGNORE INTO tickers_meta (ticker, name, sector) VALUES (?,?,?)",
        (meta["ticker"], meta.get("name"), meta.get("sector")),
    )
    conn.commit()
    conn.close()
    print(f"[INFO] Stored metadata for {meta['ticker']}")
