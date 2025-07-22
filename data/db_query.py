import sqlite3
import pandas as pd

# path to your database
DB_PATH = "./data/portfolio_data.db"

# list of test tickers
test_tickers = ['MMM', 'AOS', 'ABT', 'ABBV', 'ACN']

# connect to the database
conn = sqlite3.connect(DB_PATH)

# preview some data from daily_prices
print("\n--- Sample from daily_prices ---")
df_prices = pd.read_sql("SELECT * FROM daily_prices WHERE ticker IN ({}) LIMIT 10".format(
    ','.join(['?']*len(test_tickers))
), conn, params=test_tickers)
print(df_prices)

# preview some data from tickers_meta
print("\n--- Sample from tickers_meta ---")
df_meta = pd.read_sql("SELECT * FROM tickers_meta WHERE ticker IN ({})".format(
    ','.join(['?']*len(test_tickers))
), conn, params=test_tickers)
print(df_meta)

# delete test tickers from both tables
with conn:
    conn.executemany("DELETE FROM daily_prices WHERE ticker = ?", [(t,) for t in test_tickers])
    conn.executemany("DELETE FROM tickers_meta WHERE ticker = ?", [(t,) for t in test_tickers])

print("\n Deleted test tickers from database.")

conn.close()
