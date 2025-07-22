from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import pandas as pd
from scripts.fetch_data import fetch_prices, fetch_ticker_metadata
from scripts.store_data import store_prices, store_metadata

def log_info(msg):
    """Simple logger for Airflow and scripts."""
    print(f"[INFO] {msg}")

def ingest_all_tickers():
    df = pd.read_csv("data/constituents.csv")
    tickers = df["Symbol"].unique()
    end_date = "2025-07-18"
    start_date = "2015-07-18"
    failed_tickers = []

    for ticker in tickers:
        try:
            prices = fetch_prices(ticker, start_date, end_date)
            meta = fetch_ticker_metadata(ticker)
            if prices.empty or not meta:
                log_info(f"Skipping {ticker} due to missing data.")
                failed_tickers.append(ticker)
                continue
            store_prices(prices)
            store_metadata(meta)
        except Exception as e:
            log_info(f"Error processing {ticker}: {e}")
            failed_tickers.append(ticker)
            continue

    if failed_tickers:
        print("Failed tickers:", failed_tickers)
        # Optionally, write to a file for later retry:
        with open("data/failed_tickers.txt", "w") as f:
            for t in failed_tickers:
                f.write(f"{t}\n")

default_args = {
    "owner": "airflow",
    "start_date": datetime(2025, 7, 18),
    "retries": 1,
}

with DAG(
    "data_ingestion_dag",
    default_args=default_args,
    schedule_interval=None,  # or whatever schedule you want
    catchup=False,
) as dag:
    ingest_task = PythonOperator(
        task_id="ingest_all_tickers",
        python_callable=ingest_all_tickers,
    )