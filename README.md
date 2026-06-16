# Portfolio Risk Analysis

An interactive portfolio risk dashboard built with Streamlit, backed by a local SQLite database of historical price data sourced from Massive.com (formerly Polygon.io) and yfinance.

---

## What It Does

- Select up to 25 S&P 500 stocks and/or ETFs; SPY is always included as the market benchmark
- Filter the stock universe by GICS sector before picking
- Choose a time horizon (1, 3, 5, or 10 years) and a risk-free rate (adjustable slider)
- Computes per-asset risk metrics: Sharpe ratio, Sortino ratio, Beta, Max Drawdown, VaR (5%), and CVaR
- Computes the same metrics for the portfolio treated as a single equal-weight position
- Renders color-coded metric cards with qualitative interpretations and reference ranges
- Plots cumulative returns (individual stocks + equal-weight portfolio vs. SPY benchmark)
- Plots a Monte Carlo efficient frontier (2,500 random weight combinations) coloured by Sharpe ratio
- Shows a pairwise correlation matrix with heatmap styling
- Full dark/light mode toggle

---

## Architecture

```
Massive.com API ──► fetch_data.py ──► store_data.py ──► SQLite (daily_prices, tickers_meta)
yfinance        ──► backfill_yfinance.py ─────────────► SQLite (gap fill only)

SQLite ──► data/helpers.py ──► metrics/core.py ──► streamlit_app/app.py ──► Browser
```

Data is ingested once (or re-run to refresh) and stored locally. The Streamlit app reads only from SQLite — no live API calls at runtime.

---

## Key Engineering Decisions

**Idempotent ingestion** — both backfill scripts use `INSERT OR IGNORE` against a `(ticker, date)` unique constraint, so they can be interrupted and re-run without duplicates.

**Dual data sources for history** — Massive.com's free tier returns limited history per call (rate-limited at 5 req/min with a 13s sleep). A separate yfinance backfill script fills gaps back to 2020-01-01 with no enforced rate limit, using a shorter 0.5s courtesy sleep.

**Parameterized SQL with dynamic `IN` clause** — `helpers.get_price_data` builds `IN (?,?,?)` by joining `?` placeholders, never interpolating user input into the query string.

**Date buffer on time horizons** — the app adds an extra 60–200 day buffer when calculating `start_date` (depending on horizon) to account for trading calendar gaps and ensure the requested number of trading years is actually present in the result.

**SPY always injected as benchmark** — the app inserts SPY at index 0 of the ticker list before querying, so Beta, Sharpe, and Sortino computations always have a benchmark available regardless of user selection.

**30-ticker hard cap** — `helpers.py` raises a `ValueError` above 30 tickers to avoid runaway query sizes; the UI caps user picks at 29 (+SPY = 30).

**Reproducible efficient frontier** — `np.random.default_rng(42)` seeds the random portfolio generation. Weights are drawn from a Dirichlet distribution to guarantee they sum to 1 without renormalization.

**Dark mode CSS scoping workaround** — Streamlit popovers render in a separate stacking context where CSS custom properties (`var(--bg)`) do not resolve. Dark mode injects a second hardcoded CSS block with literal colour values specifically targeting popover elements.

**`@st.cache_data` on universe load** — the S&P 500 constituent CSV and DB ticker query are cached so sector filters and picker re-renders don't hit the DB on every interaction.

---

## Metrics and Algorithms

All metrics are computed from daily percentage returns over the selected time window.

| Metric | Approach | Note |
|---|---|---|
| Sharpe ratio | `(mean_excess_return × 252) / (std × √252)` | Annualised |
| Sortino ratio | Same numerator; denominator uses downside std only (`returns < 0`) | Penalises downside vol only |
| Beta | `cov(asset, benchmark) / var(benchmark)` | Benchmark is SPY |
| Max Drawdown | Cumulative product of `(1 + r)`, peak-to-trough percentage | Worst single drop over period |
| VaR (5%) | 5th percentile of daily return distribution | Historical, not parametric |
| CVaR | Mean of all returns ≤ VaR | Expected loss in the worst 5% of days |
| Efficient frontier | 2,500 Dirichlet-sampled random weight vectors | Illustrative only — not an optimiser |

**Limitation:** the portfolio is always equal-weighted. There is no mean-variance optimisation — the efficient frontier is a visualisation tool to show where the current portfolio sits relative to the random sample, not a recommendation engine.

---

## Setup

**Prerequisites:** Python 3.10+, a Massive.com API key (free tier works; formerly Polygon.io — existing keys still work).

```bash
# 1. Clone and install dependencies
git clone <repo-url>
cd Portfolio-Risk-Analysis
pip install -r requirements.txt

# 2. Add your Polygon API key
echo "POLYGON_API_KEY=your_key_here" > scripts/.env

# 3. Ingest price data (one-time; takes ~5 min on free tier due to rate limiting)
python scripts/ingest_all_tickers.py

# 4. Optional: backfill history to 2020-01-01
python scripts/backfill_history.py      # via Polygon (slower, rate-limited)
python scripts/backfill_yfinance.py     # via yfinance (faster, fills gaps)

# 5. Run the app
python -m streamlit run streamlit_app/Portfolio_Analyzer.py
```

---

## Project Structure

```
├── streamlit_app/
│   ├── Portfolio_Analyzer.py   # All UI, chart builders, metric card rendering
│   └── pages/
│       └── Glossary.py         # Plain-English definitions of every financial term
├── metrics/
│   └── core.py                 # Pure-function metric computations (Sharpe, VaR, etc.)
├── data/
│   ├── helpers.py              # Parameterized SQLite query layer
│   └── portfolio_data.db       # Local price database (git-ignored)
├── scripts/
│   ├── fetch_data.py           # Massive.com API client (formerly Polygon.io)
│   ├── store_data.py           # SQLite write functions
│   ├── ingest_all_tickers.py   # Initial ingestion for S&P 500 + ETF list
│   ├── backfill_history.py     # Extends history via Polygon (rate-limited)
│   ├── backfill_yfinance.py    # Fills gaps via yfinance
│   ├── utils.py                # API key loading, rate-limit sleep
│   └── .env                    # API key (git-ignored)
├── tickers/
│   └── constituents.csv        # S&P 500 constituents with GICS sectors
└── dags/
    └── data_ingestion_dag.py   # Airflow DAG scaffold (not active)
```

---

## Stack

| Layer | Technology |
|---|---|
| UI / app framework | Streamlit |
| Charts | Plotly |
| Data manipulation | pandas, NumPy |
| Database | SQLite (via `sqlite3`) |
| Primary data source | Massive.com REST API (formerly Polygon.io) |
| Backfill data source | yfinance |
| Styling | CSS custom properties injected via `st.markdown` |
| Language | Python 3.10+ |
