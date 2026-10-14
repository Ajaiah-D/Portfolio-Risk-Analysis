"""
rebuild_history.py
------------------
Re-download full price history for tickers and replace what is stored, so
every row for a ticker shares one adjustment basis.

The database was originally filled in three batches (a yfinance backfill,
Massive.com, then daily yfinance refreshes), each adjusted for splits and
dividends as of the day it ran. This script is the one-time repair for that,
and a manual tool if a ticker ever needs restating by hand. Day to day,
refresh_prices.py restates tickers on its own when it detects a change.

Uses the same safety checks as the daily refresh: a ticker is only replaced
if the fresh download covers the stored history and moves like the same
security. Delisted tickers are skipped; their stored history is left alone.

Run:
    python scripts/rebuild_history.py            # every ticker
    python scripts/rebuild_history.py NFLX CRWD  # just these
"""
import os
import sys
import time
import logging
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts import refresh_prices
from scripts.symbols import load_delisted

log = logging.getLogger(__name__)


def run(tickers=None, today=None):
    """Restate `tickers` (default: all non-delisted tickers in the database).

    Returns {"restated": [tickers], "refused": {ticker: reason}}.
    """
    today     = today or date.today()
    yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    fetch_end = today.strftime("%Y-%m-%d")
    delisted  = load_delisted()

    targets = sorted(tickers or refresh_prices.get_latest_dates())
    skipped = [t for t in targets if t in delisted]
    targets = [t for t in targets if t not in delisted]
    if skipped:
        log.info(f"Skipping delisted tickers: {skipped}")

    summary = {"restated": [], "refused": {}}
    for i, ticker in enumerate(targets, 1):
        ok, message = refresh_prices.restate_ticker(ticker, fetch_end, yesterday)
        if ok:
            summary["restated"].append(ticker)
            log.info(f"[{i}/{len(targets)}] {ticker}: {message}")
        else:
            summary["refused"][ticker] = message
            log.error(f"[{i}/{len(targets)}] {ticker}: NOT replaced — {message}")
        time.sleep(refresh_prices.SLEEP)

    log.info(f"Rebuild done. Restated {len(summary['restated'])}, "
             f"refused {len(summary['refused'])}: {summary['refused'] or 'none'}")
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout)])
    result = run(sys.argv[1:] or None)
    sys.exit(1 if result["refused"] else 0)
