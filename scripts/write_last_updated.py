"""
write_last_updated.py
----------------------
Writes data/last_updated.json — a small, git-tracked freshness signal for the
price database. Unlike portfolio_data.db (gitignored, too large for GitHub),
this file is tiny and always committed, so it's what any health check
(human, script, or AI assistant) should read to answer "is the data current?"

Run after any refresh:
    python scripts/write_last_updated.py
"""
import json
import sqlite3
import datetime

DB_PATH = "data/portfolio_data.db"
OUT_PATH = "data/last_updated.json"


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(DISTINCT ticker), MIN(date), MAX(date), COUNT(*) FROM daily_prices"
    )
    n_tickers, min_date, max_date, n_rows = cur.fetchone()
    conn.close()

    payload = {
        "last_refreshed_utc": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "ticker_count": n_tickers,
        "earliest_date": min_date,
        "latest_date": max_date,
        "total_rows": n_rows,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
