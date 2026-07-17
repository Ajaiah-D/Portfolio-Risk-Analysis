# Portfolio Risk Analysis

An interactive portfolio risk dashboard built with Streamlit, backed by a local SQLite database of historical price data sourced from Massive.com (formerly Polygon.io) and yfinance. Built for two audiences at once: people who want to understand what their portfolio actually does, and people learning what these metrics mean in the first place — every number comes with a plain-English interpretation and a full glossary.

---

## What It Does

- Select up to 25 S&P 500 stocks and/or ETFs; SPY is always included as the market benchmark (and can also be held as a position)
- **Analyze your real portfolio**: enter the dollar amount you hold in each position, or use equal weighting to explore. Set a total portfolio value and amounts auto-balance to it — edit one holding and the rest adjust, with a warning if an edit would exceed the total
- Filter the stock universe by GICS sector; choose a 1–10 year horizon and adjustable risk-free rate
- **Overview tab** — scorecard vs SPY (return, volatility, Sharpe, max drawdown), seven interpreted metric cards, and automatic plain-English insights (correlation clusters, sector concentration, risk drivers, worst month, improvement opportunities)
- **Performance tab** — cumulative returns vs SPY, per-asset metrics table, sector exposure
- **Risk tab** — underwater (drawdown) chart, rolling volatility, and rolling beta, showing *when* risk showed up rather than one number for the whole period
- **Diversification tab** — 0–100 diversification score (correlation × effective positions), correlation matrix heatmap
- **What-If & Optimize tab** — approximate max-Sharpe and min-volatility reference allocations with a suggested rebalance table, an efficient frontier (2,500 random portfolios), and live weight sliders that update every metric instantly
- **Planning tab** — Monte Carlo simulation (1,000 paths) with target value and probability of reaching it
- Portfolios are saved in the page URL — bookmark or share a link and the analysis reloads
- Full dark/light mode, onboarding flow with a one-click example portfolio

---

## Architecture

```
Massive.com API ──► fetch_data.py ──► store_data.py ──► SQLite (daily_prices, tickers_meta)
yfinance        ──► backfill_yfinance.py ─────────────► SQLite (gap fill)
yfinance        ──► refresh_prices.py ────────────────► SQLite (forward refresh)
GitHub Actions  ──► refresh_prices.py (daily, Mon–Fri) ► cache-persisted SQLite + last_updated.json

SQLite ──► data/helpers.py ──► metrics/ (core, optimize)
                                  │
                       streamlit_app/ (Portfolio_Analyzer + charts, insights, interpret, style)
```

Data is ingested once and refreshed forward on demand. The Streamlit app reads only from SQLite — no live API calls at runtime.

| Module | Responsibility |
|---|---|
| `metrics/core.py` | Pure-function metric computations (Sharpe, Sortino, Beta, drawdown, VaR/CVaR, diversification score) |
| `metrics/optimize.py` | Long-only max-Sharpe / min-volatility search (iterated Dirichlet sampling — no solver dependency) |
| `streamlit_app/charts.py` | All Plotly chart builders (pure functions of data + theme) |
| `streamlit_app/insights.py` | Rule-based plain-English findings engine |
| `streamlit_app/interpret.py` | Metric interpretations, badge ranges, card rendering, table stylers |
| `streamlit_app/style.py` | CSS theming (light/dark via custom properties) |
| `streamlit_app/Portfolio_Analyzer.py` | Orchestration: sidebar, state, tabs |

---

## Key Engineering Decisions

**Real weights, alignment-safe** — portfolio functions accept `{ticker: weight}` dicts and align them to the returns matrix internally, so column ordering can never silently mismatch weights.

**Solver-free optimisation** — max-Sharpe / min-vol weights are found by iterated Dirichlet sampling (sample the simplex, concentrate around the incumbent, repeat). Approximate but deterministic, long-only by construction, and dependency-free; validated against the two-asset analytic solution in tests.

**Diversification score with two components** — weighted average pairwise correlation (mapped over the realistic 0–0.8 range) × effective number of positions (`1/Σw²`), so both "everything moves together" and "one position dominates" pull the score down.

**Idempotent ingestion** — all ingestion scripts use `INSERT OR IGNORE` against a `(ticker, date)` unique constraint, so they can be interrupted and re-run without duplicates.

**Dual data sources for history** — Massive.com's free tier is rate-limited (5 req/min); yfinance fills history back to 2020-01-01 and refreshes forward with no enforced limit.

**Parameterized SQL with dynamic `IN` clause** — `helpers.get_price_data` builds `IN (?,?,?)` from placeholders, never interpolating user input into the query string.

**SPY as benchmark vs holding** — SPY is always fetched for Beta/benchmark computations, but only counts as a portfolio position if the user explicitly selects it.

**Shareable state in the URL** — the selected tickers, amounts, horizon, and risk-free rate are serialised into query params after each run, making any analysis a bookmarkable link.

**Dark mode CSS scoping workaround** — Streamlit popovers render in a separate stacking context where CSS custom properties don't resolve; dark mode injects a second hardcoded CSS block targeting popover elements.

**Tested at three levels** — unit tests for the metrics engine (hand-checked values), analytic-solution tests for the optimizer, and end-to-end `streamlit.testing.AppTest` runs that execute the real app headlessly (empty state, example flow, URL prefill, custom amounts).

**Automated refresh without committing the database** — the DB is gitignored because it's too large for GitHub (95MB+ and growing, close to GitHub's 100MB hard per-file limit). A daily GitHub Actions workflow persists it between runs via `actions/cache` instead of git, and refreshes it forward with `refresh_prices.py`. Only a small `data/last_updated.json` (timestamp, ticker count, date range, row count) gets committed — that's the freshness signal any health check reads, without ever touching a large binary in git history.

---

## Metrics and Algorithms

All metrics are computed from daily percentage returns over the selected time window.

| Metric | Approach | Note |
|---|---|---|
| Sharpe ratio | `(mean_excess_return × 252) / (std × √252)` | Annualised |
| Sortino ratio | Same numerator; denominator uses downside std only (`returns < 0`) | Penalises downside vol only |
| Beta | `cov(asset, benchmark) / var(benchmark)`, both ddof=1 | Benchmark is SPY |
| Max Drawdown | Cumulative product of `(1 + r)`, peak-to-trough percentage | Also shown over time (underwater chart) |
| VaR (5%) | 5th percentile of daily return distribution | Historical, not parametric |
| CVaR | Mean of all returns ≤ VaR | Expected loss in the worst 5% of days |
| Diversification score | `100 × clip((0.8 − avg_corr)/0.8) × (1 − 1/n_eff)` | Correlation + weight concentration |
| Efficient frontier | 2,500 Dirichlet-sampled random weight vectors | Illustrative |
| Max Sharpe / Min Vol | Iterated Dirichlet sampling, 5 refinement rounds | Approximate long-only optimum |
| Monte Carlo | 1,000 paths, daily normal draws from historical μ/σ | Understates tail risk (stated in-app) |

**Limitations:** optimizer allocations and Monte Carlo outcomes describe the past sample, not the future — the app labels them as study aids, not recommendations. Monte Carlo assumes normally distributed returns.

---

## Setup

**Prerequisites:** Python 3.10+, a Massive.com API key (free tier works; formerly Polygon.io — existing keys still work).

```bash
# 1. Clone and install dependencies
git clone <repo-url>
cd Portfolio-Risk-Analysis
pip install -r requirements.txt

# 2. Add your API key
echo "POLYGON_API_KEY=your_key_here" > scripts/.env

# 3. Ingest price data (one-time; takes ~5 min on free tier due to rate limiting)
python scripts/ingest_all_tickers.py

# 4. Optional: backfill history to 2020-01-01
python scripts/backfill_history.py      # via Massive.com (slower, rate-limited)
python scripts/backfill_yfinance.py     # via yfinance (faster, fills gaps)

# 5. Keep data current (run any time; idempotent)
python scripts/refresh_prices.py

# 6. Run the app
python -m streamlit run streamlit_app/Portfolio_Analyzer.py

# Run the tests
python -m pytest tests/
```

---

## Automated Data Refresh (GitHub Actions)

`.github/workflows/refresh_data.yml` runs `scripts/refresh_prices.py` automatically every weekday morning (11:00 UTC) and on manual dispatch. Since the price database is gitignored, the workflow never commits it — instead:

1. The DB is restored from **GitHub Actions cache** (persists between runs, no git history bloat).
2. `refresh_prices.py` fetches forward from each ticker's last known date.
3. `scripts/write_last_updated.py` writes `data/last_updated.json` — a timestamp, ticker count, date range, and row count.
4. The updated DB is saved back to cache; `last_updated.json` is committed **only if it changed**.
5. A rolling backup of the DB is also uploaded to a GitHub Release (`data-seed` tag) — used only if the cache is ever empty (first run, or a cache eviction).

**One-time setup:** the bootstrap fallback needs a starter DB uploaded once:

```bash
gh release create data-seed data/portfolio_data.db \
  --title "Price data seed" \
  --notes "Bootstrap fallback for the daily refresh workflow."
```

After that, the workflow is self-sufficient — no secrets beyond the default `GITHUB_TOKEN` are required.

---

## Project Structure

```
├── .github/workflows/
│   └── refresh_data.yml        # Daily automated price refresh (see above)
├── streamlit_app/
│   ├── Portfolio_Analyzer.py   # Orchestration: sidebar, session state, tabs
│   ├── charts.py               # Plotly chart builders
│   ├── insights.py             # Rule-based plain-English findings
│   ├── interpret.py            # Metric interpretations + card rendering
│   ├── style.py                # CSS theming (light/dark)
│   └── pages/
│       └── Glossary.py         # Plain-English definitions of every term used
├── metrics/
│   ├── core.py                 # Pure-function metric computations
│   └── optimize.py             # Max-Sharpe / min-vol weight search
├── data/
│   ├── helpers.py              # Parameterized SQLite query layer
│   ├── portfolio_data.db       # Local price database (git-ignored)
│   └── last_updated.json       # Freshness metadata (git-tracked, small)
├── scripts/
│   ├── fetch_data.py           # Massive.com API client (formerly Polygon.io)
│   ├── store_data.py           # SQLite write functions
│   ├── ingest_all_tickers.py   # Initial ingestion for S&P 500 + ETF list
│   ├── backfill_history.py     # Extends history via Massive.com (rate-limited)
│   ├── backfill_yfinance.py    # Fills historical gaps via yfinance
│   ├── refresh_prices.py       # Forward refresh to yesterday via yfinance
│   ├── write_last_updated.py   # Writes data/last_updated.json freshness metadata
│   ├── utils.py                # API key loading, rate-limit sleep
│   └── .env                    # API key (git-ignored)
├── tests/
│   ├── test_core.py            # Metrics engine unit tests
│   ├── test_optimize.py        # Optimizer vs analytic solutions
│   └── test_app.py             # Headless end-to-end app runs (AppTest)
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
| Backfill / refresh source | yfinance |
| Styling | CSS custom properties injected via `st.markdown` |
| Testing | pytest + `streamlit.testing.AppTest` |
| Language | Python 3.10+ |
