import sqlite3
import pandas as pd

# path to your database
DB_PATH = "./data/portfolio_data.db"

ticker = "SPY"

# connect to the database
conn = sqlite3.connect(DB_PATH)

# Join daily_prices and tickers_meta for AAPL
query = """
SELECT p.*, m.name, m.sector
FROM daily_prices p
JOIN tickers_meta m ON p.ticker = m.ticker
WHERE p.ticker = ?
ORDER BY p.date DESC
LIMIT 10
"""

df = pd.read_sql(query, conn, params=[ticker])
print(df)

conn.close()
