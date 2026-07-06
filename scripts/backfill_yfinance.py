"""
backfill_yfinance.py
--------------------
One-time historical gap fill using yfinance.
Fetches 2020-01-01 → day before your earliest existing data for every ticker in the DB.
Keeps your Polygon pipeline untouched — this only writes to the same daily_prices table.

Run:
    python scripts/backfill_yfinance.py

Monitor:
    PowerShell:  Get-Content data/backfill_yf.log -Wait
    CMD:         more +0 data\backfill_yf.log  (then keep re-running)
"""

import sys
import sqlite3
import time
import logging
from datetime import date, timedelta

import yfinance as yf
import pandas as pd

DB_PATH      = "data/portfolio_data.db"
LOG_PATH     = "data/backfill_yf.log"
TARGET_START = "2020-01-01"
SLEEP        = 0.5   # yfinance has no enforced rate limit; small sleep is courteous

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


def get_coverage():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("SELECT ticker, MIN(date) FROM daily_prices GROUP BY ticker")
    rows = cur.fetchall()
    conn.close()
    return {ticker: earliest for ticker, earliest in rows}


def insert(df):
    if df.empty:
        return 0
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    rows = [
        (str(r["date"]), r["open"], r["high"], r["low"],
         r["close"], r["volume"], r["ticker"])
        for _, r in df.iterrows()
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO daily_prices "
        "(date, open, high, low, close, volume, ticker) VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    n = cur.rowcount
    conn.commit()
    conn.close()
    return n


def fetch_yf(ticker, start, end):
    """Fetch daily OHLCV from yfinance, return cleaned DataFrame or empty."""
    try:
        raw = yf.download(
            ticker,
            start=start,
            end=end,
            auto_adjust=True,
            progress=False,
            threads=False,
        )
    except Exception as exc:
        log.warning(f"  {ticker}: yfinance exception — {exc}")
        return pd.DataFrame()

    if raw.empty:
        return pd.DataFrame()

    # yfinance returns a MultiIndex if you pass a list; flatten
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    raw = raw.rename(columns={
        "Open": "open", "High": "high", "Low": "low",
        "Close": "close", "Volume": "volume",
    })
    raw = raw[["open", "high", "low", "close", "volume"]].copy()
    raw["date"]   = raw.index.date
    raw["ticker"] = ticker
    raw = raw.dropna(subset=["close"])
    return raw.reset_index(drop=True)


def run():
    coverage = get_coverage()
    to_fill  = [
        (t, e) for t, e in coverage.items()
        if e > TARGET_START
    ]
    to_fill.sort(key=lambda x: x[0])

    log.info(f"yfinance backfill — {len(to_fill)} tickers need history before {to_fill[0][1] if to_fill else 'N/A'}")

    if not to_fill:
        log.info("All tickers already reach the target start. Nothing to do.")
        return

    total_inserted = 0
    for i, (ticker, earliest_in_db) in enumerate(to_fill, 1):
        fetch_end = (
            date.fromisoformat(earliest_in_db) - timedelta(days=1)
        ).strftime("%Y-%m-%d")

        log.info(f"[{i}/{len(to_fill)}] {ticker}  {TARGET_START} -> {fetch_end}")

        df = fetch_yf(ticker, TARGET_START, fetch_end)

        if df.empty:
            log.info(f"  {ticker}: no data returned")
            time.sleep(SLEEP)
            continue

        n = insert(df)
        total_inserted += n
        log.info(f"  {ticker}: inserted {n} rows, earliest now {df['date'].min()}")
        time.sleep(SLEEP)

    log.info(f"Done. Total rows inserted: {total_inserted}")

    # Verify final coverage
    final = get_coverage()
    reached = sum(1 for e in final.values() if e <= TARGET_START)
    log.info(f"{reached}/{len(final)} tickers now reach {TARGET_START}")


if __name__ == "__main__":
    run()
