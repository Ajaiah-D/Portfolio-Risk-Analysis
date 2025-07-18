import streamlit as st
import datetime

# set app title
st.title("📊 portfolio risk analysis tool")

# sidebar inputs
st.sidebar.header("configure portfolio")

# select number of stocks
portfolio_size = st.sidebar.slider("Select number of stocks", 3, 5, 10, 20)

# select time horizon
time_horizon = st.sidebar.radio("select time horizon", ["1 Year", "3 Years", "5 Years", "10 Years"])
time_days = {"1 Year": 252, "3 Years": 756, "5 Years": 1260, "10 Years": 2520}[time_horizon]

# input tickers
tickers = st.sidebar.text_input("enter stock tickers (comma-separated)", "AAPL,MSFT,GOOGL,TSLA")

# process tickers
tickers_list = [t.strip().upper() for t in tickers.split(',')][:portfolio_size]

# display selections
st.write(f"portfolio: {tickers_list}")
st.write(f"time horizon: {time_horizon} ({time_days} trading days)")

# run analysis button
if st.sidebar.button("run analysis"):
    st.success("analysis starting... (must connect backend")
