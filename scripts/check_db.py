import sqlite3
import pandas as pd

conn = sqlite3.connect("data/portfolio_data.db")
prices = pd.read_sql("SELECT * FROM daily_prices LIMIT 5", conn)
meta = pd.read_sql("SELECT * FROM tickers_meta LIMIT 5", conn)
conn.close()

print(prices)
print(meta)