"""
validate_data.py
----------------
Data-quality report for the price database.

Two kinds of finding:
- ERRORS break an assumption the app relies on (grain, non-null prices,
  ISO dates, every ticker having metadata). Exit code 1.
- WARNINGS need a human to look: one-day moves large enough to be an
  unadjusted stock split. Exit code 0 unless --strict is passed.

A ticker that has stopped updating is an ERROR unless it is listed in
tickers/delisted.csv: either its symbol needs fixing or someone needs to
decide it is delisted.

The daily workflow adds two time-based checks, which are errors there:
    --max-age-days N       newest price is more than N days old
    --recent-jump-days N   a suspect move dated within the last N days
                           (old ones are known history; a new one means a
                           split got past the refresh, or needs a look)

Run:
    python scripts/validate_data.py
    python scripts/validate_data.py --strict
"""
import argparse
import os
import sqlite3
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.symbols import load_delisted

DB_PATH = "data/portfolio_data.db"

# A one-day close-to-close move at least this large is treated as suspect.
# Real moves this size exist (energy names fell ~50% on 2020-03-09), so this
# is a prompt to check for an unadjusted split, not proof of one.
JUMP_THRESHOLD = 0.5
# A ticker is "stale" when its newest row is this many days behind the
# newest row in the whole table (delisted, renamed, or failing to fetch).
STALE_DAYS = 7


def _scalar(conn, sql):
    return conn.execute(sql).fetchone()[0] or 0


def check_errors(conn):
    """Return {check_name: violating_row_count} for hard invariants."""
    return {
        "duplicate_ticker_date": _scalar(conn, """
            SELECT COUNT(*) FROM (
                SELECT 1 FROM daily_prices GROUP BY ticker, date HAVING COUNT(*) > 1
            )"""),
        "missing_key": _scalar(conn,
            "SELECT COUNT(*) FROM daily_prices WHERE ticker IS NULL OR date IS NULL"),
        "missing_or_non_positive_close": _scalar(conn,
            "SELECT COUNT(*) FROM daily_prices WHERE close IS NULL OR close <= 0"),
        "high_below_low": _scalar(conn,
            "SELECT COUNT(*) FROM daily_prices WHERE high < low"),
        # Refresh logic compares dates as strings, which is only correct for
        # zero-padded ISO text.
        "non_iso_date": _scalar(conn, """
            SELECT COUNT(*) FROM daily_prices
            WHERE date IS NOT NULL AND date NOT GLOB
                  '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'"""),
        "future_date": _scalar(conn,
            "SELECT COUNT(*) FROM daily_prices WHERE date > date('now')"),
        # helpers.get_price_data inner-joins to tickers_meta, so a ticker
        # without metadata silently disappears from the app.
        "ticker_without_metadata": _scalar(conn, """
            SELECT COUNT(DISTINCT ticker) FROM daily_prices
            WHERE ticker NOT IN (SELECT ticker FROM tickers_meta)"""),
        "missing_unique_index": 0 if _scalar(conn, """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type = 'index' AND tbl_name = 'daily_prices'
              AND sql LIKE '%UNIQUE%'""") else 1,
    }


def find_suspect_jumps(conn, threshold=JUMP_THRESHOLD):
    """Return [(ticker, date, prev_close, close, pct_change)] for one-day
    moves of at least `threshold`, oldest first."""
    return conn.execute("""
        SELECT ticker, date, prev_close, close, close / prev_close - 1 AS change
        FROM (
            SELECT ticker, date, close,
                   LAG(close) OVER (PARTITION BY ticker ORDER BY date) AS prev_close
            FROM daily_prices
        )
        WHERE prev_close > 0 AND ABS(close / prev_close - 1) >= ?
        ORDER BY date, ticker
    """, (threshold,)).fetchall()


def find_stale_tickers(conn, stale_days=STALE_DAYS):
    """Return [(ticker, latest_date)] for tickers whose newest row trails the
    newest row in the table by more than `stale_days`."""
    return conn.execute("""
        WITH latest AS (
            SELECT ticker, MAX(date) AS latest_date FROM daily_prices GROUP BY ticker
        )
        SELECT ticker, latest_date FROM latest
        WHERE julianday((SELECT MAX(latest_date) FROM latest)) - julianday(latest_date) > ?
        ORDER BY latest_date, ticker
    """, (stale_days,)).fetchall()


def main(argv=None, today=None):
    parser = argparse.ArgumentParser(description="Validate the price database.")
    parser.add_argument("--db", default=DB_PATH)
    parser.add_argument("--delisted", default=None, help="path to delisted.csv")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 on warnings as well as errors")
    parser.add_argument("--max-age-days", type=int, default=None)
    parser.add_argument("--recent-jump-days", type=int, default=None)
    args = parser.parse_args(argv)
    today = today or date.today()

    conn = sqlite3.connect(args.db)
    try:
        errors = {k: v for k, v in check_errors(conn).items() if v}
        jumps = find_suspect_jumps(conn)
        stale = find_stale_tickers(conn)
        n_rows, n_tickers, max_date = conn.execute(
            "SELECT COUNT(*), COUNT(DISTINCT ticker), MAX(date) FROM daily_prices"
        ).fetchone()
    finally:
        conn.close()

    delisted = load_delisted(args.delisted)
    unexplained = [(t, d) for t, d in stale if t not in delisted]
    known = [(t, d) for t, d in stale if t in delisted]
    if unexplained:
        errors["stale_ticker_not_in_delisted_csv"] = len(unexplained)

    if args.max_age_days is not None and max_date is not None:
        if max_date < (today - timedelta(days=args.max_age_days)).isoformat():
            errors[f"newest_price_older_than_{args.max_age_days}_days"] = 1

    recent_jumps = []
    if args.recent_jump_days is not None:
        cutoff = (today - timedelta(days=args.recent_jump_days)).isoformat()
        recent_jumps = [j for j in jumps if j[1] >= cutoff]
        if recent_jumps:
            errors[f"suspect_move_in_last_{args.recent_jump_days}_days"] = len(recent_jumps)

    print(f"{n_rows:,} rows, {n_tickers} tickers, latest date {max_date}")
    print(f"\nERRORS: {len(errors)}")
    for name, count in errors.items():
        print(f"  {name}: {count}")
    for ticker, d in unexplained:
        print(f"  stale  {ticker:<6} latest {d}  (fix its symbol or add it to tickers/delisted.csv)")
    for ticker, d, prev, close, change in recent_jumps:
        print(f"  recent {ticker:<6} {d}  {prev:>10.2f} -> {close:>10.2f}  ({change:+.0%})")

    print(f"\nWARNINGS: {len(jumps)} suspect one-day moves (>= {JUMP_THRESHOLD:.0%})")
    for ticker, d, prev, close, change in jumps:
        print(f"  jump   {ticker:<6} {d}  {prev:>10.2f} -> {close:>10.2f}  ({change:+.0%})")

    print(f"\nDELISTED (history kept, not refreshed): {len(known)}")
    for ticker, d in known:
        print(f"  {ticker:<6} data ends {d}")

    if errors or (args.strict and jumps):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
