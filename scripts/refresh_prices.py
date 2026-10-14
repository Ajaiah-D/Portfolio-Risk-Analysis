"""
refresh_prices.py
-----------------
Brings every ticker's prices up to yesterday's close. Run this whenever you
want to bring prices up to date.

Safe to run repeatedly: new rows use INSERT OR IGNORE, so no duplicates.

"Up to yesterday" is deliberate: a trading day must be complete before it is
fetched, so a partial bar is never stored.

Restatements
------------
Prices are adjusted closes, and the source re-adjusts a ticker's ENTIRE
history every time it pays a dividend or splits. Appending new rows to old
ones therefore mixes two adjustment bases and produces a false jump (a
10-for-1 split shows up as a -90% day). To catch this, each refresh re-fetches
the last stored day (the "anchor") alongside the new days. If the re-fetched
anchor no longer matches what is stored, the history has been restated, and
the whole ticker is replaced from a fresh download.

Run:
    python scripts/refresh_prices.py
"""

import os
import sys
import sqlite3
import time
import logging
from datetime import date, timedelta

import yfinance as yf
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.store_data import insert_prices, replace_ticker_history, validate_prices
from scripts.symbols import load_delisted, yahoo_symbol

DB_PATH  = "data/portfolio_data.db"
LOG_PATH = "data/refresh.log"
SLEEP    = 0.5

HISTORY_START = "2020-01-01"

# Stored vs re-fetched anchor close may differ by float noise; anything past
# this relative difference means the source has re-adjusted the history.
ANCHOR_TOLERANCE = 1e-4
# Guards for replacing a ticker's history (see check_replacement).
MIN_ROW_COVERAGE     = 0.95
RETURN_MATCH_WITHIN  = 0.005
MIN_RETURN_AGREEMENT = 0.80

log = logging.getLogger(__name__)


def _configure_logging():
    """Set up file + console logging. Called only when run as a script, so
    importing this module (e.g. from tests) has no side effects."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)s  %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def get_latest_dates():
    """Return {ticker: latest_date_in_db} for all tickers."""
    return {ticker: latest for ticker, (latest, _) in get_latest_bars().items()}


def get_latest_bars():
    """Return {ticker: (latest_date, close_on_that_date)} for all tickers."""
    conn = sqlite3.connect(DB_PATH)
    try:
        # SQLite fills bare columns from the row that holds MAX(date), so
        # `close` here is the close on each ticker's latest date.
        rows = conn.execute(
            "SELECT ticker, MAX(date), close FROM daily_prices GROUP BY ticker"
        ).fetchall()
    finally:
        conn.close()
    return {ticker: (latest, close) for ticker, latest, close in rows}


def get_stored_history(ticker):
    """Return the stored (date, close) rows for one ticker as a DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql(
            "SELECT date, close FROM daily_prices WHERE ticker = ? ORDER BY date",
            conn, params=(ticker,),
        )
    finally:
        conn.close()


def fetch_yf(ticker, start, end):
    """Fetch daily bars from yfinance. `start` is inclusive and `end` is
    EXCLUSIVE: end="2026-10-13" returns bars up to 2026-10-12."""
    try:
        raw = yf.download(
            yahoo_symbol(ticker),
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


def anchor_matches(stored_close, fetched_close, tolerance=ANCHOR_TOLERANCE):
    """True if a re-fetched close equals the stored one, within float noise."""
    if not stored_close or stored_close <= 0:
        return False
    return abs(fetched_close / stored_close - 1) <= tolerance


def check_replacement(stored, fresh):
    """Decide whether `fresh` may replace `stored` (both have date + close).

    Returns (ok, reason). Replacing is destructive, so it is refused unless
    the fresh download:
    - reaches at least as far forward as what is stored,
    - has at least MIN_ROW_COVERAGE of the stored row count, and
    - moves like the same security: on shared dates, daily returns agree
      within RETURN_MATCH_WITHIN on at least MIN_RETURN_AGREEMENT of days.
      Adjustments rescale prices but leave returns alone (ex-dividend days
      aside), whereas a reused symbol has unrelated returns.
    """
    if fresh.empty:
        return False, "source returned no rows"
    if stored.empty:
        return True, "nothing stored yet"

    s = stored.assign(date=stored["date"].astype(str)).set_index("date")["close"]
    f = fresh.assign(date=fresh["date"].astype(str)).set_index("date")["close"]

    if f.index.max() < s.index.max():
        return False, f"source ends {f.index.max()}, before stored {s.index.max()}"
    if len(f) < MIN_ROW_COVERAGE * len(s):
        return False, f"source has {len(f)} rows vs {len(s)} stored"

    both = pd.concat([s.pct_change(), f.pct_change()], axis=1, join="inner").dropna()
    if len(both) >= 20:
        agreement = float(((both.iloc[:, 0] - both.iloc[:, 1]).abs() <= RETURN_MATCH_WITHIN).mean())
        if agreement < MIN_RETURN_AGREEMENT:
            return False, (f"daily returns agree on only {agreement:.0%} of shared days; "
                           "this looks like a different security")
    return True, "ok"


def restate_ticker(ticker, fetch_end, max_date):
    """Replace one ticker's history with a fresh full download.

    Returns (ok, message). On refusal nothing is changed.
    """
    fresh = fetch_yf(ticker, HISTORY_START, fetch_end)
    if not fresh.empty:
        fresh, rejected = validate_prices(fresh, max_date=max_date)
        if rejected:
            log.warning(f"  {ticker}: rejected rows in full download {rejected}")
    ok, reason = check_replacement(get_stored_history(ticker), fresh)
    if not ok:
        return False, reason
    deleted, inserted = replace_ticker_history(fresh, ticker, DB_PATH)
    return True, f"replaced {deleted} rows with {inserted}"


def run(today=None):
    """Bring every ticker up to yesterday.

    Returns {"inserted": row_count, "restated": [tickers], "refused": [tickers]}.
    `today` is injectable for tests; it defaults to the current date.
    """
    today     = today or date.today()
    yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    # yfinance's `end` is exclusive, so asking for bars up to and including
    # yesterday means passing today. Passing yesterday (the old behaviour)
    # silently left the database one trading day behind on every run. Today
    # itself is never fetched, so a still-trading day's partial bar is never
    # stored.
    fetch_end = today.strftime("%Y-%m-%d")
    delisted  = load_delisted()
    summary   = {"inserted": 0, "restated": [], "refused": []}

    to_update = sorted(
        (ticker, latest_date, close)
        for ticker, (latest_date, close) in get_latest_bars().items()
        if latest_date < yesterday and ticker not in delisted
    )

    if not to_update:
        log.info("All tickers are already up to date.")
        return summary

    log.info(f"Refreshing {len(to_update)} tickers up to {yesterday}")

    for i, (ticker, latest_date, stored_close) in enumerate(to_update, 1):
        log.info(f"[{i}/{len(to_update)}] {ticker}  {latest_date} -> {yesterday}")

        # Start AT the latest stored date, not after it: that bar is the anchor.
        df = fetch_yf(ticker, latest_date, fetch_end)
        time.sleep(SLEEP)

        if df.empty:
            log.info(f"  {ticker}: no new data")
            continue

        df, rejected = validate_prices(df, max_date=yesterday)
        if rejected:
            log.warning(f"  {ticker}: rejected rows {rejected}")

        dates  = df["date"].astype(str)
        anchor = df[dates == latest_date]
        new    = df[dates > latest_date]

        if not anchor.empty and not anchor_matches(stored_close, float(anchor["close"].iloc[0])):
            ok, message = restate_ticker(ticker, fetch_end, yesterday)
            time.sleep(SLEEP)
            if ok:
                summary["restated"].append(ticker)
                log.info(f"  {ticker}: history restated by source; {message}")
            else:
                # Appending here would splice two adjustment bases (or two
                # different securities) together, so store nothing.
                summary["refused"].append(ticker)
                log.error(f"  {ticker}: anchor mismatch but restatement refused: {message}")
            continue

        if new.empty:
            log.info(f"  {ticker}: no new data")
            continue

        n = insert_prices(new, DB_PATH)
        summary["inserted"] += n
        log.info(f"  {ticker}: inserted {n} rows, latest now {new['date'].max()}")

    log.info(f"Done. Rows inserted: {summary['inserted']}. "
             f"Restated: {len(summary['restated'])}. Refused: {summary['refused'] or 'none'}")
    return summary


if __name__ == "__main__":
    _configure_logging()
    run()
