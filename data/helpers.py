import sqlite3
import pandas as pd

DB_PATH = "data/portfolio_data.db"

def get_price_data(tickers, start_date, end_date):
    """
    Query daily_prices joined to tickers_meta, filter to tickers + dates, sort by date.
    Returns DataFrame: date (datetime64[ns]), ticker (str), close (float), name, sector.
    """
    if not tickers:
        raise ValueError("Tickers list cannot be empty.")
    if len(tickers) > 10:
        raise ValueError("Max 10 tickers allowed per query for performance/safety.")

    placeholders = ','.join(['?'] * len(tickers))
    query = f"""
        SELECT p.date, p.ticker, p.close, m.name, m.sector
        FROM daily_prices p
        JOIN tickers_meta m ON p.ticker = m.ticker
        WHERE p.ticker IN ({placeholders})
          AND p.date BETWEEN ? AND ?
        ORDER BY p.date ASC, p.ticker ASC
    """

    params = list(tickers) + [start_date, end_date]
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(query, conn, params=params)
    conn.close()

    # Clean up types
    df['date'] = pd.to_datetime(df['date'])
    df['ticker'] = df['ticker'].astype(str)
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df = df.drop_duplicates(subset=['date', 'ticker'])
    df = df.sort_values(['date', 'ticker'])

    # Optional: drop rows with missing close
    df = df.dropna(subset=['close'])

    return df[['date', 'ticker', 'close', 'name', 'sector']]