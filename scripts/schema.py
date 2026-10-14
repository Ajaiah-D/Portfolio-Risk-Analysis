"""Database schema, defined in code.

Every write path calls ensure_schema() first, so a brand-new database gets
the same tables and constraints as the existing one. Everything is
IF NOT EXISTS, so it is a no-op against a database that already has them.

Grain: daily_prices holds one row per (ticker, date). The unique index is
what makes INSERT OR IGNORE idempotent - without it, re-running an ingestion
script would silently store duplicate rows.
"""

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS daily_prices (
        date   DATE,
        open   REAL,
        high   REAL,
        low    REAL,
        close  REAL,
        volume REAL,
        ticker TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS tickers_meta (
        ticker TEXT,
        name   TEXT,
        sector TEXT
    )""",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_prices_unique ON daily_prices (ticker, date)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_meta_ticker ON tickers_meta (ticker)",
]


def ensure_schema(conn):
    """Create tables and unique indexes if they are missing."""
    for statement in SCHEMA:
        conn.execute(statement)
    conn.commit()
