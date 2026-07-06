"""
refresh_prices.py
-----------------
Fetches missing price data from the latest date in the DB up to yesterday
for every ticker. Run this whenever you want to bring prices up to date.

Safe to run repeatedly — uses INSERT OR IGNORE, so no duplicates.

Run:
    python scripts/refresh_prices.py
"""

import sys
import sqlite3
import time
import logging
from datetime import date, timedelta

import yfinance as yf
import pandas as pd

DB_PATH  = "data/portfolio_data.db"
LOG_PATH = "data/refresh.log"
SLEEP    = 0.5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


def get_latest_dates():
    """Return {ticker: latest_date_in_db} for all tickers."""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("SELECT ticker, MAX(date) FROM daily_prices GROUP BY ticker")
    rows = cur.fetchall()
    conn.close()
    return {ticker: latest for ticker, latest in rows}


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
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    latest    = get_latest_dates()

    to_update = [
        (ticker, latest_date)
        for ticker, latest_date in latest.items()
        if latest_date < yesterday
    ]
    to_update.sort(key=lambda x: x[0])

    if not to_update:
        log.info("All tickers are already up to date.")
        return

    log.info(f"Refreshing {len(to_update)} tickers up to {yesterday}")

    total_inserted = 0
    for i, (ticker, latest_date) in enumerate(to_update, 1):
        fetch_start = (
            date.fromisoformat(latest_date) + timedelta(days=1)
        ).strftime("%Y-%m-%d")

        log.info(f"[{i}/{len(to_update)}] {ticker}  {fetch_start} -> {yesterday}")

        df = fetch_yf(ticker, fetch_start, yesterday)

        if df.empty:
            log.info(f"  {ticker}: no new data")
            time.sleep(SLEEP)
            continue

        n = insert(df)
        total_inserted += n
        log.info(f"  {ticker}: inserted {n} rows, latest now {df['date'].max()}")
        time.sleep(SLEEP)

    log.info(f"Done. Total rows inserted: {total_inserted}")


if __name__ == "__main__":
    run()
