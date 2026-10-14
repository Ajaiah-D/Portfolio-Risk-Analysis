"""Ticker symbol helpers shared by ingestion, validation and the app."""
import csv
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DELISTED_PATH = os.path.join(_ROOT, "tickers", "delisted.csv")


def yahoo_symbol(ticker):
    """Yahoo writes share classes with a hyphen (BRK-B); the database and the
    S&P constituents file use a dot (BRK.B)."""
    return ticker.replace(".", "-")


def load_delisted(path=None):
    """Return {ticker: reason} for symbols that no longer have a usable price
    feed. Their stored history is kept and shown, but they are never refreshed
    and cannot be analysed past the date their data ends.

    The list is a tracked file on purpose: taking a ticker out of the daily
    refresh is a decision someone should review, not something the pipeline
    should infer from one failed download.
    """
    return {t: row.get("reason", "") for t, row in _read(path).items()}


def load_last_valid_dates(path=None):
    """Return {ticker: 'YYYY-MM-DD'} for delisted tickers whose stored rows
    after that date are known to be wrong (e.g. the symbol was reused by a
    different security and the old refresh appended its prices)."""
    return {t: row["last_valid_date"] for t, row in _read(path).items()
            if (row.get("last_valid_date") or "").strip()}


def _read(path=None):
    path = path or DELISTED_PATH
    if not os.path.exists(path):
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return {row["ticker"]: row for row in csv.DictReader(f)}
