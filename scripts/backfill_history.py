"""
backfill_history.py
-------------------
Extends historical price data in the DB as far back as Polygon's free tier allows.

- Reads every ticker currently in the DB
- For each, fetches prices from TARGET_START up to the earliest date already stored
- Skips tickers that already have data back to TARGET_START
- Respects the free-tier rate limit (5 calls/minute → 13s sleep between calls)
- Logs all activity to data/backfill.log so you can tail it in a separate terminal
- Safe to interrupt and re-run: never inserts duplicate rows

Run in background (Windows):
    pythonw -c "exec(open('scripts/backfill_history.py').read())"
Or just in a terminal you can leave open:
    python scripts/backfill_history.py
"""

import sys
import sqlite3
import time
import logging
from datetime import date, timedelta

sys.path.insert(0, ".")
from scripts.fetch_data import fetch_prices
from scripts.store_data import store_prices

# ── Config ────────────────────────────────────────────────────────────────────
DB_PATH        = "data/portfolio_data.db"
LOG_PATH       = "data/backfill.log"
TARGET_START   = "2020-01-01"   # Aim for ~6 years; Polygon free tier returns what it can
SLEEP_SECONDS  = 13             # 5 calls/min free tier → ~13s between calls
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


def get_ticker_coverage():
    """Return dict of {ticker: earliest_date_in_db} for all tickers."""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("SELECT ticker, MIN(date) FROM daily_prices GROUP BY ticker")
    rows = cur.fetchall()
    conn.close()
    return {ticker: earliest for ticker, earliest in rows}


def already_covered(earliest_in_db: str) -> bool:
    """True if we already have data at or before TARGET_START."""
    return earliest_in_db <= TARGET_START


def insert_without_duplicates(df):
    """Store prices using INSERT OR IGNORE — skips any (ticker, date) that already exists."""
    if df.empty:
        return 0
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    rows = [
        (str(row["date"]), row["open"], row["high"],
         row["low"], row["close"], row["volume"], row["ticker"])
        for _, row in df.iterrows()
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO daily_prices "
        "(date, open, high, low, close, volume, ticker) VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    inserted = cur.rowcount
    conn.commit()
    conn.close()
    return inserted


def run_backfill():
    coverage = get_ticker_coverage()
    total    = len(coverage)
    skipped  = sum(1 for e in coverage.values() if already_covered(e))

    log.info(f"Backfill starting — {total} tickers in DB, {skipped} already reach {TARGET_START}")

    to_fill = [(t, e) for t, e in coverage.items() if not already_covered(e)]
    to_fill.sort(key=lambda x: x[0])  # alphabetical for predictable ordering

    log.info(f"{len(to_fill)} tickers need backfilling")

    if not to_fill:
        log.info("Nothing to do — all tickers already reach the target start date.")
        return

    for i, (ticker, earliest_in_db) in enumerate(to_fill, 1):
        # Fetch up to one day before what we already have to avoid overlap
        fetch_end = (
            date.fromisoformat(earliest_in_db) - timedelta(days=1)
        ).strftime("%Y-%m-%d")

        log.info(
            f"[{i}/{len(to_fill)}] {ticker}  —  fetching {TARGET_START} → {fetch_end}"
            f"  (currently starts {earliest_in_db})"
        )

        try:
            df = fetch_prices(ticker, TARGET_START, fetch_end)
        except Exception as exc:
            log.warning(f"  {ticker}: fetch failed — {exc}")
            time.sleep(SLEEP_SECONDS)
            continue

        if df.empty:
            log.info(f"  {ticker}: no data returned for this range (free-tier limit likely reached)")
            time.sleep(SLEEP_SECONDS)
            continue

        n = insert_without_duplicates(df)
        new_earliest = df["date"].min()
        log.info(f"  {ticker}: inserted {n} rows, new earliest = {new_earliest}")
        time.sleep(SLEEP_SECONDS)

    # Summary
    final_coverage = get_ticker_coverage()
    reached = sum(1 for e in final_coverage.values() if already_covered(e))
    log.info(
        f"Backfill complete. {reached}/{total} tickers now reach {TARGET_START}. "
        f"Check {LOG_PATH} for full details."
    )


if __name__ == "__main__":
    run_backfill()
