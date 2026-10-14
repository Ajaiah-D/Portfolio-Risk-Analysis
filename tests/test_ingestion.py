"""Ingestion and data-validation tests.

No network and no real database: every test builds a temporary SQLite file,
and the yfinance call is replaced with a fake that honours the same contract
(start inclusive, end EXCLUSIVE).
"""
import json
import os
import sqlite3
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
import pytest

from data import helpers
from scripts import (rebuild_history, refresh_prices, store_data, symbols,
                     validate_data, write_last_updated)
from scripts.schema import ensure_schema

# The schema the production database was originally created with (by pandas),
# including its redundant non-unique index. Used to prove ensure_schema() is a
# no-op against the real thing.
LEGACY_DDL = [
    'CREATE TABLE "daily_prices" ("date" DATE, "open" REAL, "high" REAL, '
    '"low" REAL, "close" REAL, "volume" REAL, "ticker" TEXT)',
    'CREATE TABLE "tickers_meta" ("ticker" TEXT, "name" TEXT, "sector" TEXT)',
    "CREATE INDEX idx_prices_ticker_date ON daily_prices (ticker, date)",
    "CREATE UNIQUE INDEX idx_prices_unique ON daily_prices (ticker, date)",
    "CREATE UNIQUE INDEX idx_meta_ticker ON tickers_meta (ticker)",
]


def bars(ticker, dates, close=100.0):
    """Price rows for `ticker` on each date (date objects or ISO strings)."""
    return pd.DataFrame({
        "date": [date.fromisoformat(d) if isinstance(d, str) else d for d in dates],
        "open": close, "high": close + 1, "low": close - 1,
        "close": close, "volume": 1000.0, "ticker": ticker,
    })


def rows(db, sql="SELECT ticker, date, close FROM daily_prices ORDER BY ticker, date"):
    conn = sqlite3.connect(db)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


@pytest.fixture
def db(tmp_path):
    """Path to a database file that does not exist yet."""
    return str(tmp_path / "prices.db")


# ── Schema ────────────────────────────────────────────────────────────────────
class TestSchema:
    def _objects(self, db):
        return {name for (name,) in rows(db, "SELECT name FROM sqlite_master")}

    def test_creates_tables_and_unique_indexes_on_empty_db(self, db):
        conn = sqlite3.connect(db)
        ensure_schema(conn)
        conn.close()
        assert {"daily_prices", "tickers_meta", "idx_prices_unique", "idx_meta_ticker"} \
            <= self._objects(db)

    def test_is_idempotent(self, db):
        conn = sqlite3.connect(db)
        ensure_schema(conn)
        ensure_schema(conn)
        conn.close()
        assert len(self._objects(db)) == 4

    def test_no_op_on_existing_production_schema(self, db):
        conn = sqlite3.connect(db)
        for ddl in LEGACY_DDL:
            conn.execute(ddl)
        conn.execute("INSERT INTO daily_prices VALUES ('2026-01-02',1,2,0.5,1.5,10,'AAA')")
        conn.commit()
        before = rows(db, "SELECT type, name, sql FROM sqlite_master ORDER BY name")
        ensure_schema(conn)
        conn.close()
        assert rows(db, "SELECT type, name, sql FROM sqlite_master ORDER BY name") == before
        assert rows(db) == [("AAA", "2026-01-02", 1.5)]

    def test_unique_index_rejects_duplicate_grain(self, db):
        conn = sqlite3.connect(db)
        ensure_schema(conn)
        conn.execute("INSERT INTO daily_prices (date, close, ticker) VALUES ('2026-01-02', 1, 'AAA')")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO daily_prices (date, close, ticker) VALUES ('2026-01-02', 2, 'AAA')")
        conn.close()

    def test_refuses_to_index_a_table_that_already_has_duplicates(self, db):
        # A database that was written without the index can't be silently
        # "fixed" - the failure has to be loud.
        conn = sqlite3.connect(db)
        conn.execute(LEGACY_DDL[0])
        for _ in range(2):
            conn.execute("INSERT INTO daily_prices (date, close, ticker) VALUES ('2026-01-02', 1, 'AAA')")
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            ensure_schema(conn)
        conn.close()


# ── Inserts ───────────────────────────────────────────────────────────────────
class TestInsertPrices:
    def test_works_on_a_database_with_no_tables(self, db):
        assert store_data.insert_prices(bars("AAA", ["2026-01-02", "2026-01-05"]), db) == 2
        assert len(rows(db)) == 2

    def test_rerun_inserts_nothing(self, db):
        df = bars("AAA", ["2026-01-02", "2026-01-05"])
        store_data.insert_prices(df, db)
        assert store_data.insert_prices(df, db) == 0
        assert len(rows(db)) == 2

    def test_overlapping_batch_inserts_only_new_rows(self, db):
        store_data.insert_prices(bars("AAA", ["2026-01-02", "2026-01-05"]), db)
        n = store_data.insert_prices(bars("AAA", ["2026-01-05", "2026-01-06", "2026-01-07"]), db)
        assert n == 2
        assert [r[1] for r in rows(db)] == ["2026-01-02", "2026-01-05", "2026-01-06", "2026-01-07"]

    def test_same_date_different_tickers_both_stored(self, db):
        store_data.insert_prices(bars("AAA", ["2026-01-02"]), db)
        assert store_data.insert_prices(bars("BBB", ["2026-01-02"]), db) == 1

    def test_existing_row_is_never_overwritten(self, db):
        # Documents the trade-off of INSERT OR IGNORE: a corrected price for a
        # date already stored is dropped. Restating history needs a different path.
        store_data.insert_prices(bars("AAA", ["2026-01-02"], close=100.0), db)
        assert store_data.insert_prices(bars("AAA", ["2026-01-02"], close=50.0), db) == 0
        assert rows(db) == [("AAA", "2026-01-02", 100.0)]

    def test_empty_frame_is_a_no_op(self, db):
        assert store_data.insert_prices(pd.DataFrame(), db) == 0
        assert not os.path.exists(db)

    def test_dates_stored_as_iso_text(self, db):
        # refresh_prices compares dates as strings; that is only correct for
        # zero-padded ISO text.
        store_data.insert_prices(bars("AAA", [date(2026, 1, 2)]), db)
        assert rows(db, "SELECT date, typeof(date) FROM daily_prices") == [("2026-01-02", "text")]

    def test_metadata_insert_is_idempotent_on_fresh_db(self, db):
        meta = {"ticker": "AAA", "name": "Alpha", "sector": "Tech"}
        store_data.store_metadata(meta, db)
        store_data.store_metadata({**meta, "name": "Changed"}, db)
        assert rows(db, "SELECT ticker, name FROM tickers_meta") == [("AAA", "Alpha")]


# ── Batch validation ──────────────────────────────────────────────────────────
class TestValidatePrices:
    def test_clean_batch_passes_unchanged(self):
        df = bars("AAA", ["2026-01-02", "2026-01-05"])
        clean, rejected = store_data.validate_prices(df, max_date="2026-01-05")
        assert rejected == {}
        pd.testing.assert_frame_equal(clean, df)

    def test_missing_column_raises(self):
        with pytest.raises(ValueError, match="volume"):
            store_data.validate_prices(bars("AAA", ["2026-01-02"]).drop(columns=["volume"]))

    def test_drops_missing_close(self):
        df = bars("AAA", ["2026-01-02", "2026-01-05"])
        df.loc[1, "close"] = np.nan
        clean, rejected = store_data.validate_prices(df)
        assert rejected == {"missing_close": 1}
        assert len(clean) == 1

    @pytest.mark.parametrize("bad", [0.0, -5.0])
    def test_drops_non_positive_close(self, bad):
        df = bars("AAA", ["2026-01-02", "2026-01-05"])
        df.loc[0, "close"] = bad
        clean, rejected = store_data.validate_prices(df)
        assert rejected == {"non_positive_close": 1}
        assert clean["close"].tolist() == [100.0]

    def test_drops_rows_after_max_date(self):
        df = bars("AAA", ["2026-01-05", "2026-01-06", "2026-01-07"])
        clean, rejected = store_data.validate_prices(df, max_date="2026-01-06")
        assert rejected == {"after_max_date": 1}
        assert [str(d) for d in clean["date"]] == ["2026-01-05", "2026-01-06"]

    def test_drops_duplicates_within_batch_keeping_last(self):
        df = pd.concat([bars("AAA", ["2026-01-02"], close=1.0),
                        bars("AAA", ["2026-01-02"], close=2.0)], ignore_index=True)
        clean, rejected = store_data.validate_prices(df)
        assert rejected == {"duplicate_in_batch": 1}
        assert clean["close"].tolist() == [2.0]

    def test_drops_missing_key(self):
        df = bars("AAA", ["2026-01-02", "2026-01-05"])
        df["ticker"] = df["ticker"].astype(object)
        df.loc[0, "ticker"] = None
        clean, rejected = store_data.validate_prices(df)
        assert rejected == {"missing_key": 1}

    def test_does_not_mutate_input(self):
        df = bars("AAA", ["2026-01-02", "2026-01-05"])
        df.loc[0, "close"] = -1.0
        snapshot = df.copy()
        store_data.validate_prices(df)
        pd.testing.assert_frame_equal(df, snapshot)


# ── Daily refresh ─────────────────────────────────────────────────────────────
# Tue 2026-10-13 is "today"; Mon 10-12 is the last complete trading day.
TODAY = date(2026, 10, 13)
TRADING_DAYS = ["2026-10-07", "2026-10-08", "2026-10-09", "2026-10-12", "2026-10-13"]


class FakeYahoo:
    """Stands in for refresh_prices.fetch_yf with yfinance's date contract:
    start is inclusive, end is exclusive."""

    def __init__(self, trading_days=TRADING_DAYS, fail=(), empty=()):
        self.trading_days = trading_days
        self.fail = set(fail)
        self.empty = set(empty)
        self.calls = []

    def __call__(self, ticker, start, end):
        self.calls.append((ticker, start, end))
        if ticker in self.fail:
            raise RuntimeError("simulated network failure")
        days = [d for d in self.trading_days if start <= d < end]
        if ticker in self.empty or not days:
            return pd.DataFrame()
        return bars(ticker, days)


@pytest.fixture
def refresh_db(db, monkeypatch):
    """Temp DB wired into refresh_prices, with sleeps removed."""
    monkeypatch.setattr(refresh_prices, "DB_PATH", db)
    monkeypatch.setattr(refresh_prices, "SLEEP", 0)
    return db


def seed(db, ticker, through):
    """Store every trading day up to and including `through`."""
    store_data.insert_prices(bars(ticker, [d for d in TRADING_DAYS if d <= through]), db)


class TestRefresh:
    def test_latest_dates_per_ticker(self, refresh_db):
        seed(refresh_db, "AAA", "2026-10-09")
        seed(refresh_db, "BBB", "2026-10-07")
        assert refresh_prices.get_latest_dates() == {"AAA": "2026-10-09", "BBB": "2026-10-07"}

    def test_fetches_through_yesterday(self, refresh_db, monkeypatch):
        # Regression test for the off-by-one: with an exclusive `end`, passing
        # yesterday left Monday's close unfetched on Tuesday.
        seed(refresh_db, "AAA", "2026-10-09")
        fake = FakeYahoo()
        monkeypatch.setattr(refresh_prices, "fetch_yf", fake)

        result = refresh_prices.run(today=TODAY)

        # start is the latest stored date (the anchor bar); end is today, exclusive
        assert fake.calls == [("AAA", "2026-10-09", "2026-10-13")]
        assert result == {"inserted": 1, "restated": [], "refused": []}
        assert refresh_prices.get_latest_dates() == {"AAA": "2026-10-12"}

    def test_never_stores_today_even_if_source_returns_it(self, refresh_db, monkeypatch):
        # A source that ignores `end` and returns today's partial bar must not
        # get it into the table, because rows are never overwritten.
        seed(refresh_db, "AAA", "2026-10-09")
        leaky = lambda ticker, start, end: bars(ticker, ["2026-10-12", "2026-10-13"])
        monkeypatch.setattr(refresh_prices, "fetch_yf", leaky)

        refresh_prices.run(today=TODAY)

        assert refresh_prices.get_latest_dates() == {"AAA": "2026-10-12"}

    def test_skips_tickers_already_at_yesterday(self, refresh_db, monkeypatch):
        seed(refresh_db, "AAA", "2026-10-12")
        fake = FakeYahoo()
        monkeypatch.setattr(refresh_prices, "fetch_yf", fake)
        assert refresh_prices.run(today=TODAY)["inserted"] == 0
        assert fake.calls == []

    def test_second_run_same_day_inserts_nothing(self, refresh_db, monkeypatch):
        seed(refresh_db, "AAA", "2026-10-07")
        monkeypatch.setattr(refresh_prices, "fetch_yf", FakeYahoo())
        assert refresh_prices.run(today=TODAY)["inserted"] == 3
        before = rows(refresh_db)
        assert refresh_prices.run(today=TODAY)["inserted"] == 0
        assert rows(refresh_db) == before

    def test_catches_up_after_missed_days(self, refresh_db, monkeypatch):
        seed(refresh_db, "AAA", "2026-10-07")
        monkeypatch.setattr(refresh_prices, "fetch_yf", FakeYahoo())
        refresh_prices.run(today=TODAY)
        assert [r[1] for r in rows(refresh_db)] == TRADING_DAYS[:4]

    @pytest.mark.parametrize("today", [date(2026, 10, 10), date(2026, 10, 11), date(2026, 10, 12)])
    def test_weekend_and_monday_runs_add_nothing_and_do_not_crash(self, refresh_db, monkeypatch, today):
        # Fri 10-09 is stored. Sat/Sun/Mon runs have no completed trading day to add.
        seed(refresh_db, "AAA", "2026-10-09")
        monkeypatch.setattr(refresh_prices, "fetch_yf", FakeYahoo())
        assert refresh_prices.run(today=today) == {"inserted": 0, "restated": [], "refused": []}
        assert refresh_prices.get_latest_dates() == {"AAA": "2026-10-09"}

    def test_fetch_window_is_never_inverted(self, refresh_db, monkeypatch):
        for through in TRADING_DAYS[:4]:
            seed(refresh_db, "T" + through[-2:], through)
        fake = FakeYahoo()
        monkeypatch.setattr(refresh_prices, "fetch_yf", fake)
        refresh_prices.run(today=TODAY)
        assert fake.calls and all(start < end for _, start, end in fake.calls)

    def test_delisted_tickers_are_not_fetched(self, refresh_db, monkeypatch):
        seed(refresh_db, "AAA", "2026-10-09")
        seed(refresh_db, "GONE", "2026-10-07")
        fake = FakeYahoo()
        monkeypatch.setattr(refresh_prices, "fetch_yf", fake)
        monkeypatch.setattr(refresh_prices, "load_delisted", lambda: {"GONE": "delisted"})
        refresh_prices.run(today=TODAY)
        assert [c[0] for c in fake.calls] == ["AAA"]
        assert refresh_prices.get_latest_dates()["GONE"] == "2026-10-07"

    def test_one_empty_ticker_does_not_block_the_rest(self, refresh_db, monkeypatch):
        for t in ("AAA", "BBB", "CCC"):
            seed(refresh_db, t, "2026-10-09")
        monkeypatch.setattr(refresh_prices, "fetch_yf", FakeYahoo(empty={"BBB"}))
        assert refresh_prices.run(today=TODAY)["inserted"] == 2
        assert refresh_prices.get_latest_dates() == {
            "AAA": "2026-10-12", "BBB": "2026-10-09", "CCC": "2026-10-12"}

    def test_bad_rows_are_rejected_good_rows_kept(self, refresh_db, monkeypatch):
        seed(refresh_db, "AAA", "2026-10-08")

        def with_bad_row(ticker, start, end):
            df = bars(ticker, ["2026-10-09", "2026-10-12"])
            df.loc[0, "close"] = 0.0
            return df

        monkeypatch.setattr(refresh_prices, "fetch_yf", with_bad_row)
        assert refresh_prices.run(today=TODAY)["inserted"] == 1
        assert [r[1] for r in rows(refresh_db)][-2:] == ["2026-10-08", "2026-10-12"]


class TestFetchYf:
    """fetch_yf's normalisation of what yfinance returns."""

    def _raw(self, closes):
        idx = pd.to_datetime(["2026-10-09", "2026-10-12"])
        cols = pd.MultiIndex.from_product(
            [["Close", "High", "Low", "Open", "Volume"], ["AAA"]], names=["Price", "Ticker"])
        data = np.column_stack([closes, [11, 12], [9, 10], [10, 11], [500, 600]])
        return pd.DataFrame(data, index=idx, columns=cols)

    def test_flattens_columns_and_adds_keys(self, monkeypatch):
        monkeypatch.setattr(refresh_prices.yf, "download", lambda *a, **k: self._raw([10.5, 11.5]))
        df = refresh_prices.fetch_yf("AAA", "2026-10-09", "2026-10-13")
        assert list(df.columns) == ["open", "high", "low", "close", "volume", "date", "ticker"]
        assert df["date"].tolist() == [date(2026, 10, 9), date(2026, 10, 12)]
        assert df["ticker"].unique().tolist() == ["AAA"]
        assert df["close"].tolist() == [10.5, 11.5]

    def test_passes_dates_through_and_requests_adjusted_prices(self, monkeypatch):
        seen = {}

        def fake_download(ticker, **kwargs):
            seen.update(kwargs, ticker=ticker)
            return self._raw([10.5, 11.5])

        monkeypatch.setattr(refresh_prices.yf, "download", fake_download)
        refresh_prices.fetch_yf("AAA", "2026-10-09", "2026-10-13")
        assert (seen["ticker"], seen["start"], seen["end"]) == ("AAA", "2026-10-09", "2026-10-13")
        assert seen["auto_adjust"] is True

    def test_share_class_symbol_is_translated_for_yahoo_only(self, monkeypatch):
        seen = {}

        def fake_download(symbol, **kwargs):
            seen["symbol"] = symbol
            return self._raw([10.5, 11.5])

        monkeypatch.setattr(refresh_prices.yf, "download", fake_download)
        df = refresh_prices.fetch_yf("BRK.B", "2026-10-09", "2026-10-13")
        assert seen["symbol"] == "BRK-B"
        assert df["ticker"].unique().tolist() == ["BRK.B"]

    def test_drops_rows_with_no_close(self, monkeypatch):
        monkeypatch.setattr(refresh_prices.yf, "download", lambda *a, **k: self._raw([np.nan, 11.5]))
        assert refresh_prices.fetch_yf("AAA", "a", "b")["close"].tolist() == [11.5]

    def test_empty_response_returns_empty_frame(self, monkeypatch):
        monkeypatch.setattr(refresh_prices.yf, "download", lambda *a, **k: pd.DataFrame())
        assert refresh_prices.fetch_yf("AAA", "a", "b").empty

    def test_exception_returns_empty_frame(self, monkeypatch):
        def boom(*a, **k):
            raise ConnectionError("down")
        monkeypatch.setattr(refresh_prices.yf, "download", boom)
        assert refresh_prices.fetch_yf("AAA", "a", "b").empty


# ── Freshness metadata ────────────────────────────────────────────────────────
def test_write_last_updated_reports_table_contents(db, tmp_path, monkeypatch):
    seed(db, "AAA", "2026-10-12")
    seed(db, "BBB", "2026-10-08")
    out = tmp_path / "last_updated.json"
    monkeypatch.setattr(write_last_updated, "DB_PATH", db)
    monkeypatch.setattr(write_last_updated, "OUT_PATH", str(out))

    write_last_updated.main()

    payload = json.loads(out.read_text())
    assert payload["ticker_count"] == 2
    assert payload["earliest_date"] == "2026-10-07"
    assert payload["latest_date"] == "2026-10-12"
    assert payload["total_rows"] == 6


# ── Whole-database validation ─────────────────────────────────────────────────
@pytest.fixture
def clean_db(db):
    """A small database with no data-quality problems."""
    days = [(date(2026, 9, 1) + timedelta(days=i)).isoformat() for i in range(30)]
    days = [d for d in days if date.fromisoformat(d).weekday() < 5]
    for t in ("AAA", "BBB"):
        store_data.insert_prices(bars(t, days), db)
        store_data.store_metadata({"ticker": t, "name": t, "sector": "X"}, db)
    return db


def run_sql(db, *statements):
    conn = sqlite3.connect(db)
    for s in statements:
        conn.execute(s)
    conn.commit()
    conn.close()


class TestValidateData:
    def _errors(self, db):
        conn = sqlite3.connect(db)
        try:
            return {k: v for k, v in validate_data.check_errors(conn).items() if v}
        finally:
            conn.close()

    def test_clean_database_has_no_findings(self, clean_db, capsys):
        assert self._errors(clean_db) == {}
        assert validate_data.main(["--db", clean_db, "--strict"]) == 0
        assert "ERRORS: 0" in capsys.readouterr().out

    def test_detects_duplicates_and_missing_index(self, clean_db):
        run_sql(clean_db, "DROP INDEX idx_prices_unique",
                "INSERT INTO daily_prices SELECT * FROM daily_prices WHERE ticker='AAA' LIMIT 3")
        assert self._errors(clean_db) == {"duplicate_ticker_date": 3, "missing_unique_index": 1}

    def test_detects_bad_close(self, clean_db):
        run_sql(clean_db,
                "UPDATE daily_prices SET close = 0 WHERE ticker='AAA' AND date='2026-09-01'",
                "UPDATE daily_prices SET close = NULL WHERE ticker='AAA' AND date='2026-09-02'")
        assert self._errors(clean_db) == {"missing_or_non_positive_close": 2}

    def test_detects_high_below_low(self, clean_db):
        run_sql(clean_db, "UPDATE daily_prices SET high = 1, low = 2 WHERE date='2026-09-01'")
        assert self._errors(clean_db) == {"high_below_low": 2}

    @pytest.mark.parametrize("bad_date", ["2026-9-3", "09/03/2026", "2026-09-03 00:00:00"])
    def test_detects_non_iso_dates(self, clean_db, bad_date):
        run_sql(clean_db, f"UPDATE daily_prices SET date='{bad_date}' "
                          "WHERE ticker='AAA' AND date='2026-09-03'")
        assert "non_iso_date" in self._errors(clean_db)

    def test_detects_future_dates(self, clean_db):
        run_sql(clean_db, "UPDATE daily_prices SET date='2999-01-01' "
                          "WHERE ticker='AAA' AND date='2026-09-03'")
        assert self._errors(clean_db) == {"future_date": 1}

    def test_detects_ticker_without_metadata(self, clean_db):
        run_sql(clean_db, "DELETE FROM tickers_meta WHERE ticker='BBB'")
        assert self._errors(clean_db) == {"ticker_without_metadata": 1}

    def test_errors_fail_the_run(self, clean_db):
        run_sql(clean_db, "UPDATE daily_prices SET close = -1 WHERE date='2026-09-01'")
        assert validate_data.main(["--db", clean_db]) == 1

    def test_flags_unadjusted_split_as_a_jump(self, clean_db, capsys):
        # A 10-for-1 split that one batch adjusted for and the next did not.
        run_sql(clean_db, "UPDATE daily_prices SET close = close * 10 "
                          "WHERE ticker='AAA' AND date >= '2026-09-15'")
        conn = sqlite3.connect(clean_db)
        jumps = validate_data.find_suspect_jumps(conn)
        conn.close()
        assert [(t, d) for t, d, *_ in jumps] == [("AAA", "2026-09-15")]
        assert jumps[0][4] == pytest.approx(9.0)
        # A warning, not an error: default run passes, --strict fails.
        assert validate_data.main(["--db", clean_db]) == 0
        assert validate_data.main(["--db", clean_db, "--strict"]) == 1
        assert "jump   AAA" in capsys.readouterr().out

    def test_ordinary_moves_are_not_flagged(self, clean_db):
        run_sql(clean_db, "UPDATE daily_prices SET close = close * 1.2 "
                          "WHERE ticker='AAA' AND date >= '2026-09-15'")
        conn = sqlite3.connect(clean_db)
        assert validate_data.find_suspect_jumps(conn) == []
        conn.close()

    def test_jump_is_measured_within_a_ticker_not_across(self, clean_db):
        # BBB trading at 10x AAA's price is not a jump.
        run_sql(clean_db, "UPDATE daily_prices SET close = close * 10 WHERE ticker='BBB'")
        conn = sqlite3.connect(clean_db)
        assert validate_data.find_suspect_jumps(conn) == []
        conn.close()

    def test_flags_ticker_that_stopped_updating(self, clean_db):
        run_sql(clean_db, "DELETE FROM daily_prices WHERE ticker='BBB' AND date > '2026-09-10'")
        conn = sqlite3.connect(clean_db)
        assert validate_data.find_stale_tickers(conn) == [("BBB", "2026-09-10")]
        conn.close()

    def test_stale_ticker_is_an_error_until_listed_as_delisted(self, clean_db, tmp_path, capsys):
        run_sql(clean_db, "DELETE FROM daily_prices WHERE ticker='BBB' AND date > '2026-09-10'")
        empty = tmp_path / "none.csv"
        empty.write_text("ticker,reason\n")
        listed = tmp_path / "delisted.csv"
        listed.write_text("ticker,reason\nBBB,acquired\n")

        assert validate_data.main(["--db", clean_db, "--delisted", str(empty)]) == 1
        assert "stale  BBB" in capsys.readouterr().out
        assert validate_data.main(["--db", clean_db, "--delisted", str(listed)]) == 0
        assert "BBB    data ends 2026-09-10" in capsys.readouterr().out

    def test_max_age_days_fails_when_newest_price_is_old(self, clean_db):
        # clean_db's newest row is 2026-09-30
        args = ["--db", clean_db, "--max-age-days", "4"]
        assert validate_data.main(args, today=date(2026, 10, 2)) == 0
        assert validate_data.main(args, today=date(2026, 10, 4)) == 0
        assert validate_data.main(args, today=date(2026, 10, 5)) == 1

    def test_recent_jump_fails_but_old_jump_only_warns(self, clean_db):
        run_sql(clean_db, "UPDATE daily_prices SET close = close * 10 "
                          "WHERE ticker='AAA' AND date >= '2026-09-15'")
        args = ["--db", clean_db, "--recent-jump-days", "30"]
        assert validate_data.main(args, today=date(2026, 9, 20)) == 1
        assert validate_data.main(args, today=date(2026, 12, 1)) == 0


# ── Restatement (splits and dividends) ────────────────────────────────────────
def weekdays(start, n):
    out, d = [], date.fromisoformat(start)
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def walk(n, seed=1, start=100.0):
    """A random-walk close series with ~1.5% daily moves."""
    rng = np.random.default_rng(seed)
    return start * np.cumprod(1 + rng.normal(0, 0.015, n))


def series_frame(ticker, dates, closes):
    df = bars(ticker, dates)
    df["close"] = np.asarray(closes, dtype=float)
    df["high"], df["low"], df["open"] = df["close"] + 1, df["close"] - 1, df["close"]
    return df


HIST_DAYS = weekdays("2026-08-03", 51)      # ends Mon 2026-10-12
assert HIST_DAYS[-1] == "2026-10-12" and HIST_DAYS[-2] == "2026-10-09"


class Source:
    """A price source holding one full close series per ticker, served with
    yfinance's date contract (start inclusive, end exclusive)."""

    def __init__(self, **series):
        self.series = series
        self.calls = []

    def __call__(self, ticker, start, end):
        self.calls.append((ticker, start, end))
        closes = self.series.get(ticker)
        if closes is None:
            return pd.DataFrame()
        keep = [(d, c) for d, c in zip(HIST_DAYS[-len(closes):], closes) if start <= d < end]
        if not keep:
            return pd.DataFrame()
        return series_frame(ticker, [d for d, _ in keep], [c for _, c in keep])


class TestAnchorMatches:
    def test_identical_close_matches(self):
        assert refresh_prices.anchor_matches(123.45, 123.45)

    def test_float_noise_matches(self):
        assert refresh_prices.anchor_matches(123.45, 123.45 * (1 + 1e-6))

    def test_dividend_sized_difference_does_not_match(self):
        assert not refresh_prices.anchor_matches(100.0, 99.5)

    def test_split_sized_difference_does_not_match(self):
        assert not refresh_prices.anchor_matches(1000.0, 100.0)

    @pytest.mark.parametrize("stored", [0.0, None, -1.0])
    def test_unusable_stored_close_never_matches(self, stored):
        assert not refresh_prices.anchor_matches(stored, 100.0)


class TestCheckReplacement:
    def _frame(self, closes, dates=None):
        return pd.DataFrame({"date": dates or HIST_DAYS[-len(closes):], "close": closes})

    def test_split_rescaled_history_is_accepted(self):
        base = walk(50)
        ok, _ = refresh_prices.check_replacement(self._frame(base), self._frame(base / 10))
        assert ok

    def test_dividend_adjusted_history_is_accepted(self):
        base = walk(50)
        adjusted = base.copy()
        adjusted[:30] *= 0.99          # a 1% dividend re-adjusts everything before it
        ok, _ = refresh_prices.check_replacement(self._frame(base), self._frame(adjusted))
        assert ok

    def test_stored_history_with_a_false_jump_can_still_be_repaired(self):
        clean = walk(50)
        broken = clean.copy()
        broken[25:] *= 10              # the unadjusted-split artifact being fixed
        ok, _ = refresh_prices.check_replacement(self._frame(broken), self._frame(clean))
        assert ok

    def test_different_security_under_same_symbol_is_refused(self):
        ok, reason = refresh_prices.check_replacement(
            self._frame(walk(50, seed=1)), self._frame(walk(50, seed=2, start=7.0)))
        assert not ok and "different security" in reason

    def test_source_with_much_less_history_is_refused(self):
        base = walk(50)
        ok, reason = refresh_prices.check_replacement(self._frame(base), self._frame(base[-10:]))
        assert not ok and "rows" in reason

    def test_source_ending_before_stored_data_is_refused(self):
        base = walk(50)
        ok, reason = refresh_prices.check_replacement(
            self._frame(base), self._frame(base[:-1], HIST_DAYS[-50:-1]))
        assert not ok and "before stored" in reason

    def test_empty_source_is_refused(self):
        ok, reason = refresh_prices.check_replacement(self._frame(walk(50)), pd.DataFrame())
        assert not ok and "no rows" in reason

    def test_anything_is_accepted_when_nothing_is_stored(self):
        ok, _ = refresh_prices.check_replacement(
            pd.DataFrame(columns=["date", "close"]), self._frame(walk(50)))
        assert ok


class TestReplaceTickerHistory:
    def test_replaces_only_the_named_ticker(self, db):
        store_data.insert_prices(bars("AAA", ["2026-01-02", "2026-01-05"], close=100.0), db)
        store_data.insert_prices(bars("BBB", ["2026-01-02"], close=7.0), db)
        result = store_data.replace_ticker_history(
            bars("AAA", ["2026-01-02", "2026-01-05", "2026-01-06"], close=50.0), "AAA", db)
        assert result == (2, 3)
        assert rows(db) == [("AAA", "2026-01-02", 50.0), ("AAA", "2026-01-05", 50.0),
                            ("AAA", "2026-01-06", 50.0), ("BBB", "2026-01-02", 7.0)]

    def test_failed_replacement_leaves_old_history_intact(self, db):
        store_data.insert_prices(bars("AAA", ["2026-01-02", "2026-01-05"], close=100.0), db)
        before = rows(db)
        bad = pd.concat([bars("AAA", ["2026-01-02"], close=50.0)] * 2, ignore_index=True)
        with pytest.raises(sqlite3.IntegrityError):
            store_data.replace_ticker_history(bad, "AAA", db)   # duplicate grain
        assert rows(db) == before

    def test_refuses_empty_replacement(self, db):
        store_data.insert_prices(bars("AAA", ["2026-01-02"]), db)
        with pytest.raises(ValueError):
            store_data.replace_ticker_history(pd.DataFrame(), "AAA", db)
        assert len(rows(db)) == 1

    def test_refuses_rows_for_another_ticker(self, db):
        with pytest.raises(ValueError):
            store_data.replace_ticker_history(bars("BBB", ["2026-01-02"]), "AAA", db)


class TestRefreshRestatement:
    """End-to-end: stored history through Fri 10-09, refresh run on Tue 10-13."""

    def _store(self, db, ticker, closes):
        store_data.insert_prices(series_frame(ticker, HIST_DAYS[:len(closes)], closes), db)

    def _jumps(self, db):
        conn = sqlite3.connect(db)
        try:
            return validate_data.find_suspect_jumps(conn)
        finally:
            conn.close()

    def test_split_triggers_full_restatement_with_no_false_jump(self, refresh_db, monkeypatch):
        truth = walk(51)
        self._store(refresh_db, "AAA", truth[:50] * 10)        # stored before a 10-for-1 split
        source = Source(AAA=truth)                              # source now fully adjusted
        monkeypatch.setattr(refresh_prices, "fetch_yf", source)

        result = refresh_prices.run(today=TODAY)

        assert result == {"inserted": 0, "restated": ["AAA"], "refused": []}
        stored = rows(refresh_db)
        assert [r[1] for r in stored] == HIST_DAYS
        assert [r[2] for r in stored] == pytest.approx(truth)
        assert self._jumps(refresh_db) == []

    def test_without_restatement_the_same_split_would_be_a_false_jump(self, refresh_db):
        # What the old append-only refresh produced; this is the bug being fixed.
        truth = walk(51)
        self._store(refresh_db, "AAA", truth[:50] * 10)
        store_data.insert_prices(series_frame("AAA", HIST_DAYS[50:], truth[50:]), refresh_db)
        assert [(t, d) for t, d, *_ in self._jumps(refresh_db)] == [("AAA", "2026-10-12")]

    def test_dividend_triggers_restatement(self, refresh_db, monkeypatch):
        truth = walk(51)
        self._store(refresh_db, "AAA", truth[:50] / 0.99)       # stored before a 1% dividend
        monkeypatch.setattr(refresh_prices, "fetch_yf", Source(AAA=truth))
        assert refresh_prices.run(today=TODAY)["restated"] == ["AAA"]
        assert [r[2] for r in rows(refresh_db)] == pytest.approx(truth)

    def test_unchanged_history_is_appended_not_restated(self, refresh_db, monkeypatch):
        truth = walk(51)
        self._store(refresh_db, "AAA", truth[:50])
        source = Source(AAA=truth)
        monkeypatch.setattr(refresh_prices, "fetch_yf", source)
        assert refresh_prices.run(today=TODAY) == {"inserted": 1, "restated": [], "refused": []}
        assert len(source.calls) == 1                           # no full-history download

    def test_reused_symbol_is_refused_and_nothing_is_stored(self, refresh_db, monkeypatch):
        self._store(refresh_db, "AAA", walk(50, seed=1))
        before = rows(refresh_db)
        impostor = Source(AAA=walk(51, seed=2, start=7.0))      # a different security
        monkeypatch.setattr(refresh_prices, "fetch_yf", impostor)

        result = refresh_prices.run(today=TODAY)

        assert result == {"inserted": 0, "restated": [], "refused": ["AAA"]}
        assert rows(refresh_db) == before

    def test_one_restatement_does_not_disturb_other_tickers(self, refresh_db, monkeypatch):
        a, b = walk(51, seed=1), walk(51, seed=2)
        self._store(refresh_db, "AAA", a[:50] * 4)
        self._store(refresh_db, "BBB", b[:50])
        monkeypatch.setattr(refresh_prices, "fetch_yf", Source(AAA=a, BBB=b))
        assert refresh_prices.run(today=TODAY) == {"inserted": 1, "restated": ["AAA"], "refused": []}
        assert [r[2] for r in rows(refresh_db) if r[0] == "BBB"] == pytest.approx(b)

    def test_second_run_after_restatement_changes_nothing(self, refresh_db, monkeypatch):
        truth = walk(51)
        self._store(refresh_db, "AAA", truth[:50] * 10)
        monkeypatch.setattr(refresh_prices, "fetch_yf", Source(AAA=truth))
        refresh_prices.run(today=TODAY)
        before = rows(refresh_db)
        assert refresh_prices.run(today=TODAY) == {"inserted": 0, "restated": [], "refused": []}
        assert rows(refresh_db) == before


class TestRebuildHistory:
    def test_restates_everything_except_delisted(self, refresh_db, monkeypatch):
        a, gone = walk(51, seed=1), walk(40, seed=3)
        store_data.insert_prices(series_frame("AAA", HIST_DAYS[:50], a[:50] * 10), refresh_db)
        store_data.insert_prices(series_frame("GONE", HIST_DAYS[:40], gone), refresh_db)
        source = Source(AAA=a)
        monkeypatch.setattr(refresh_prices, "fetch_yf", source)
        monkeypatch.setattr(rebuild_history, "load_delisted", lambda: {"GONE": "delisted"})

        result = rebuild_history.run(today=TODAY)

        assert result == {"restated": ["AAA"], "refused": {}}
        assert [c[0] for c in source.calls] == ["AAA"]
        assert [r[2] for r in rows(refresh_db) if r[0] == "GONE"] == pytest.approx(gone)

    def test_reports_refusals_and_keeps_their_data(self, refresh_db, monkeypatch):
        store_data.insert_prices(series_frame("AAA", HIST_DAYS[:50], walk(50)), refresh_db)
        before = rows(refresh_db)
        monkeypatch.setattr(refresh_prices, "fetch_yf", Source())      # source has nothing
        monkeypatch.setattr(rebuild_history, "load_delisted", lambda: {})
        result = rebuild_history.run(today=TODAY)
        assert result["restated"] == [] and "AAA" in result["refused"]
        assert rows(refresh_db) == before


# ── Symbols and the delisted list ─────────────────────────────────────────────
class TestSymbols:
    @pytest.mark.parametrize("ticker, expected", [("BRK.B", "BRK-B"), ("BF.B", "BF-B"), ("AAPL", "AAPL")])
    def test_yahoo_symbol(self, ticker, expected):
        assert symbols.yahoo_symbol(ticker) == expected

    def test_load_delisted_reads_csv(self, tmp_path):
        f = tmp_path / "d.csv"
        f.write_text("ticker,reason\nWBA,taken private\n")
        assert symbols.load_delisted(str(f)) == {"WBA": "taken private"}

    def test_missing_file_means_nothing_is_delisted(self, tmp_path):
        assert symbols.load_delisted(str(tmp_path / "absent.csv")) == {}

    def test_repo_delisted_file_is_well_formed(self):
        with open(symbols.DELISTED_PATH, encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        assert lines[0] == "ticker,reason"
        tickers = [l.split(",")[0] for l in lines[1:]]
        assert tickers and len(tickers) == len(set(tickers))
        assert all(l.split(",", 1)[1] for l in lines[1:]), "every entry needs a reason"


# ── Ended tickers (what the app refuses to analyse) ───────────────────────────
class TestFindEndedTickers:
    def _df(self, **rows_per_ticker):
        frames = [bars(t, HIST_DAYS[:n]) for t, n in rows_per_ticker.items()]
        df = pd.concat(frames, ignore_index=True)
        df["date"] = pd.to_datetime(df["date"])
        return df

    def test_ticker_that_stopped_early_is_reported_with_its_last_date(self):
        df = self._df(SPY=51, AAA=51, GONE=30)
        assert helpers.find_ended_tickers(df, ["AAA", "GONE"]) == {
            "GONE": date.fromisoformat(HIST_DAYS[29])}

    def test_current_tickers_are_not_reported(self):
        assert helpers.find_ended_tickers(self._df(SPY=51, AAA=51), ["AAA"]) == {}

    def test_a_few_days_behind_is_tolerated(self):
        # 3 trading days behind the benchmark is a late fetch, not a delisting
        assert helpers.find_ended_tickers(self._df(SPY=51, AAA=48), ["AAA"]) == {}

    def test_only_requested_tickers_are_checked(self):
        df = self._df(SPY=51, AAA=51, GONE=30)
        assert helpers.find_ended_tickers(df, ["AAA"]) == {}

    def test_no_benchmark_means_no_verdict(self):
        assert helpers.find_ended_tickers(self._df(AAA=51, GONE=30), ["AAA", "GONE"]) == {}
