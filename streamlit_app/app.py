import streamlit as st
import datetime
import pandas as pd
import numpy as np
import sys
sys.path.append('./data')
sys.path.append('./metrics')
from data import helpers
from metrics import core

st.title("📊 Portfolio Risk Analysis Tool")

# Sidebar inputs
st.sidebar.header("Configure Portfolio")

# Select time horizon
time_horizon = st.sidebar.radio("Select time horizon", ["1 Year", "3 Years", "5 Years", "10 Years"])
time_days = {"1 Year": 252, "3 Years": 756, "5 Years": 1260, "10 Years": 2520}[time_horizon]
end_date = datetime.date.today()
start_date = end_date - datetime.timedelta(days=time_days + int(time_days * 0.3))  # Add buffer for weekends/holidays

# Input tickers (comma-separated)
tickers_input = st.sidebar.text_input("Enter stock tickers (comma-separated)", "AAPL,MSFT,GOOGL,TSLA")
tickers_list = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]
if "SPY" not in tickers_list:
    tickers_list.insert(0, "SPY")  # Ensure SPY is included

# Limit to 10 tickers
tickers_list = tickers_list[:10]

st.write(f"Portfolio tickers: {tickers_list}")
st.write(f"Time horizon: {time_horizon} ({start_date} to {end_date})")

# Portfolio weights (equal weight for demo)
weights = [1/len(tickers_list)] * len(tickers_list)

if st.sidebar.button("Run Analysis"):
    try:
        df = helpers.get_price_data(tickers_list, str(start_date), str(end_date))
        st.write("Sample price data:", df.head())

        asset_df = core.compute_asset_metrics(df, benchmark_ticker="SPY", risk_free_rate=0.0)
        st.subheader("Asset Metrics")
        st.dataframe(asset_df.style.format("{:.3f}"))

        port_dict, corr = core.compute_portfolio_metrics(df, weights, benchmark_ticker="SPY", risk_free_rate=0.0)
        st.subheader("Portfolio Metrics")
        st.json({k: float(v) if isinstance(v, np.generic) else v for k, v in port_dict.items()})

        st.subheader("Correlation Matrix")
        st.dataframe(corr.style.format("{:.2f}"))
    except Exception as e:
        st.error(f"Error running analysis: {e}")