import os
import sqlite3
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.schema import ensure_schema

DB_PATH = "data/portfolio_data.db"

PRICE_COLUMNS = ["date", "open", "high", "low", "close", "volume", "ticker"]


def validate_prices(df, max_date=None):
    """Drop rows that must never reach daily_prices.

    Returns (clean_df, rejected) where rejected is {reason: row_count}.
    Rows are stored with INSERT OR IGNORE and never overwritten, so a bad row
    that gets in stays in - this is the only gate.

    max_date: latest allowed date as 'YYYY-MM-DD'. The daily refresh passes
    yesterday so a still-trading day's partial bar can never be stored.
    """
    missing = [c for c in PRICE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Price data is missing columns: {missing}")

    rejected = {}
    out = df.copy()

    def _drop(mask, reason):
        nonlocal out
        n = int(mask.sum())
        if n:
            rejected[reason] = n
            out = out[~mask]

    _drop(out["ticker"].isna() | out["date"].isna(), "missing_key")
    close = pd.to_numeric(out["close"], errors="coerce")
    _drop(close.isna(), "missing_close")
    close = pd.to_numeric(out["close"], errors="coerce")
    _drop(close <= 0, "non_positive_close")
    if max_date is not None:
        _drop(out["date"].astype(str) > str(max_date), "after_max_date")
    _drop(out.duplicated(subset=["ticker", "date"], keep="last"), "duplicate_in_batch")

    return out.reset_index(drop=True), rejected


def insert_prices(df, db_path=None):
    """Insert price rows, skipping any (ticker, date) already stored.

    Returns the number of rows actually inserted. Safe to call repeatedly:
    INSERT OR IGNORE against the (ticker, date) unique index, which
    ensure_schema() guarantees exists even on a brand-new database.
    """
    if df.empty:
        return 0
    conn = sqlite3.connect(db_path or DB_PATH)
    try:
        ensure_schema(conn)
        rows = [
            (str(r["date"]), r["open"], r["high"], r["low"], r["close"], r["volume"], r["ticker"])
            for _, r in df.iterrows()
        ]
        before = conn.total_changes
        conn.executemany(
            "INSERT OR IGNORE INTO daily_prices "
            "(date, open, high, low, close, volume, ticker) VALUES (?,?,?,?,?,?,?)",
            rows,
        )
        inserted = conn.total_changes - before
        conn.commit()
    finally:
        conn.close()
    return inserted


def replace_ticker_history(df, ticker, db_path=None):
    """Replace every stored row for `ticker` with `df`, atomically.

    This is the one path that overwrites prices. It exists because the source
    re-adjusts a ticker's whole history after a split or dividend, and
    INSERT OR IGNORE can never pick that up. Delete and insert run in one
    transaction, so a failure leaves the old history intact.

    Returns (rows_deleted, rows_inserted).
    """
    if df.empty:
        raise ValueError(f"Refusing to replace {ticker} history with no rows.")
    if set(df["ticker"]) != {ticker}:
        raise ValueError(f"Replacement rows must all be for {ticker}.")
    rows = [
        (str(r["date"]), r["open"], r["high"], r["low"], r["close"], r["volume"], r["ticker"])
        for _, r in df.iterrows()
    ]
    conn = sqlite3.connect(db_path or DB_PATH)
    try:
        ensure_schema(conn)
        with conn:  # commits on success, rolls back on any exception
            deleted = conn.execute(
                "DELETE FROM daily_prices WHERE ticker = ?", (ticker,)
            ).rowcount
            conn.executemany(
                "INSERT INTO daily_prices "
                "(date, open, high, low, close, volume, ticker) VALUES (?,?,?,?,?,?,?)",
                rows,
            )
    finally:
        conn.close()
    return deleted, len(rows)


def trim_after(ticker, last_valid_date, db_path=None):
    """Delete a ticker's rows dated after `last_valid_date`. Returns the
    number deleted; a no-op once the bad rows are gone."""
    conn = sqlite3.connect(db_path or DB_PATH)
    try:
        ensure_schema(conn)
        with conn:
            return conn.execute(
                "DELETE FROM daily_prices WHERE ticker = ? AND date > ?",
                (ticker, str(last_valid_date)),
            ).rowcount
    finally:
        conn.close()


def store_prices(df):
    """
    Store daily price data in the daily_prices table.
    Expects a DataFrame with columns: date, open, high, low, close, volume, ticker.
    Safe to call again for a ticker that's already partially stored.
    """
    if df.empty:
        print("[INFO] No price data to store.")
        return
    inserted = insert_prices(df)
    print(f"[INFO] Stored {inserted} new price rows for {df['ticker'].iloc[0]}")


def store_metadata(meta, db_path=None):
    """
    Store ticker metadata in the tickers_meta table.
    Expects a dict with keys: ticker, name, sector.
    Uses INSERT OR IGNORE against a unique index on ticker, so re-running for
    a ticker that already has metadata is a no-op rather than a duplicate row.
    """
    if not meta or not meta.get("ticker"):
        print("[INFO] No metadata to store.")
        return
    conn = sqlite3.connect(db_path or DB_PATH)
    try:
        ensure_schema(conn)
        conn.execute(
            "INSERT OR IGNORE INTO tickers_meta (ticker, name, sector) VALUES (?,?,?)",
            (meta["ticker"], meta.get("name"), meta.get("sector")),
        )
        conn.commit()
    finally:
        conn.close()
    print(f"[INFO] Stored metadata for {meta['ticker']}")
