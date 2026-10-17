# Portfolio Risk Analysis

**[Live demo →](https://ajaiah-d-portfolio-risk--streamlit-appportfolio-analyzer-ij9gqb.streamlit.app/)**

An interactive portfolio risk dashboard built with Streamlit, deployed on Streamlit Community Cloud, backed by a SQLite database of historical price data sourced from Massive.com (formerly Polygon.io) and yfinance. Built for two audiences at once: people who want to understand what their portfolio actually does, and people learning what these metrics mean in the first place. Every number comes with a plain-English interpretation and a full glossary.

---

## What It Does

- Search and select up to 25 stocks and ETFs from a universe of 500+ S&P 500 constituents plus 30+ ETFs across broad market, sector, bond, dividend, real asset, and international categories; SPY is always included as the market benchmark (and can also be held as a position)
- **Analyze your real portfolio**: enter the dollar amount you hold in each position, or use equal weighting to explore. Set a total portfolio value and amounts auto-balance to it — edit one holding and the rest adjust, with a warning if an edit would exceed the total
- Filter the stock universe by GICS sector; choose a 1, 3, 5 or 10 year horizon and a risk-free rate adjustable in 0.1% steps
- **Overview tab** — scorecard vs SPY (return, volatility, Sharpe, max drawdown), seven interpreted metric cards, and automatic plain-English insights (correlation clusters, sector concentration, risk drivers, worst month, improvement opportunities)
- **Performance tab** — cumulative returns vs SPY, per-asset metrics table, sector exposure
- **Risk tab** — underwater (drawdown) chart, rolling volatility, and rolling beta, showing *when* risk showed up rather than one number for the whole period
- **Diversification tab** — 0–100 diversification score (correlation × effective positions), correlation matrix heatmap
- **What-If & Optimize tab** — approximate max-Sharpe and min-volatility reference allocations with a suggested rebalance table, an efficient frontier (2,500 random portfolios), and live weight sliders that update every metric instantly
- **Planning tab** — Monte Carlo simulation (1,000 paths) with target value and probability of reaching it, fully recalculated on every input change
- Portfolios are saved in the page URL — bookmark or share a link and the analysis reloads
- Light and dark themes (switch from the ⋮ menu; follows the device by default), onboarding flow with a one-click example portfolio

---

## Architecture

```
Massive.com API ──► fetch_data.py ──► store_data.py ──► SQLite (daily_prices, tickers_meta)
yfinance        ──► backfill_yfinance.py ─────────────► SQLite (gap fill)
yfinance        ──► refresh_prices.py ────────────────► SQLite (forward refresh + restatements)
GitHub Actions  ──► refresh_prices.py (daily, Mon–Fri) ► cache-persisted SQLite + last_updated.json
                ──► validate_data.py (after each refresh) ► red run if the data needs a human
                                                                     │
                                                     GitHub Release (data-seed, rolling backup)
                                                                     │
                                                     Streamlit Cloud ► downloads DB on cold start
                                                                     │
SQLite ──► data/helpers.py ──► metrics/ (core, optimize, allocation)
                                  │
                       streamlit_app/ (Portfolio_Analyzer + charts, insights, interpret, style)
```

A diagram of the full system is in docs/architecture.excalidraw (open it at excalidraw.com).

Data is ingested once and refreshed forward daily. The Streamlit app itself never calls a live pricing API — it only reads SQLite. On Streamlit Cloud, where the database can't be committed to git, the app downloads it once per cold start from the same GitHub Release the automation keeps fresh, then behaves identically to a local run.

| Module | Responsibility |
|---|---|
| `metrics/core.py` | Pure-function metric computations (Sharpe, Sortino, Beta, drawdown, VaR/CVaR, diversification score) |
| `metrics/optimize.py` | Long-only max-Sharpe / min-volatility search (iterated Dirichlet sampling — no solver dependency) |
| `streamlit_app/allocation.py` | Budget-constrained dollar allocation: locks edited holdings, auto-balances the rest to a target total |
| `streamlit_app/charts.py` | All Plotly chart builders (pure functions of data; theme-neutral so they follow light/dark) |
| `streamlit_app/insights.py` | Rule-based plain-English findings engine |
| `streamlit_app/interpret.py` | Metric interpretations, badge ranges, card rendering, table stylers |
| `streamlit_app/style.py` | CSS for the app's own HTML cards only; light/dark itself is Streamlit's native theme (`.streamlit/config.toml`) |
| `streamlit_app/Portfolio_Analyzer.py` | Orchestration: DB bootstrap, sidebar, state, tabs |

---

## Key Engineering Decisions

**Deployable without committing the database** — the price database is gitignored: about 105MB as of October 2026, over GitHub's 100MB per-file limit, and growing by roughly 520 rows every trading day (`data/last_updated.json` has the current row count). Streamlit Cloud's container starts with no local disk state, so the app checks for the database on startup and downloads it from a GitHub Release if it's missing, then proceeds exactly as it would locally. The same release is updated every weekday by the ingestion automation with prices through the previous trading day's close.

**Budget-constrained allocation, not just weights** — `allocation.py` treats a portfolio value as a real budget: editing one holding's dollar amount locks it and re-splits the remainder across the rest so the total always equals the budget, and an edit that would exceed it is rejected with a warning instead of silently accepted. Kept as pure functions so the rebalancing rules (including the exact "$5 across 4 holdings" edge case) are unit-tested independent of any UI state.

**Real weights, alignment-safe** — portfolio functions accept `{ticker: weight}` dicts and align them to the returns matrix internally, so column ordering can never silently mismatch weights.

**Solver-free optimisation** — max-Sharpe / min-vol weights are found by iterated Dirichlet sampling (sample the simplex, concentrate around the incumbent, repeat). Approximate but deterministic, long-only by construction, and dependency-free; validated against the two-asset analytic solution in tests.

**Diversification score with two components** — weighted average pairwise correlation (mapped over the realistic 0–0.8 range) × effective number of positions (`1/Σw²`), so both "everything moves together" and "one position dominates" pull the score down.

**Idempotent ingestion, schema in code** — every write goes through one function (`store_data.insert_prices`) that uses `INSERT OR IGNORE` against a `(ticker, date)` unique index, so scripts can be interrupted and re-run without duplicates. `scripts/schema.py` creates the tables and that index if they are missing, so a brand-new database gets the same guarantee. Rows are only ever overwritten through the restatement path below.

**Only complete trading days are stored** — the daily refresh fetches through yesterday and never today, and `validate_prices` rejects any row dated later than that, because a partial bar would never be corrected. yfinance's `end` date is exclusive; an earlier version passed yesterday as `end` and so ran one trading day behind on every run while the workflow stayed green. The fix is pinned by a regression test that fakes the same exclusive-end contract.

**Restate a ticker when the source re-adjusts it** — prices are adjusted closes, and Yahoo re-adjusts a ticker's entire history every time it pays a dividend or splits. Appending new rows to old ones mixes two adjustment bases: a 10-for-1 split shows up as a −90% day. So each refresh also re-fetches the last stored day (the anchor) and compares it to what is stored. If it no longer matches, the whole ticker is replaced from a fresh download, in one transaction. Split flags from the source were not usable for this: CRWD's split is dated after the day its data broke. Replacement is refused unless the fresh history covers the stored one and its daily returns match on at least 80% of shared days, which is what stopped `PARA` (the symbol now belongs to a different security) from being overwritten. `scripts/rebuild_history.py` runs the same replacement for every ticker; it was used once to repair history that had been loaded in three differently-adjusted batches.

**Delisted tickers are kept, labelled and refused** — `tickers/delisted.csv` lists symbols with no usable price feed. Their history stays in the database and in the picker (labelled with the date their data ends), but they are not refreshed, and the app will not analyse a portfolio that holds one: past its last price a holding would be forward-filled as a flat line, quietly understating risk. The app explains which holding and why. The list is a reviewed file rather than something the pipeline infers, so one failed download never takes a ticker out of service. An optional `last_valid_date` column removes rows known to be wrong: before the restatement guard existed, the refresh appended another security's prices to `PARA` after the symbol was reused, and those rows are trimmed on every run.

**Validation as an alarm, not a gate** — `scripts/validate_data.py` checks grain, prices, date format, metadata coverage, freshness, stale tickers not on the delisted list, and split-sized one-day moves. Bad rows are already blocked before insert, so in the workflow it runs after the data is saved and turns the run red for a human to look, rather than discarding a day's data.

**Dual data sources for history** — Massive.com's free tier is rate-limited (5 req/min); yfinance fills history back to 2020-01-01 and refreshes forward with no enforced limit.

**Parameterized SQL with dynamic `IN` clause** — `helpers.get_price_data` builds `IN (?,?,?)` from placeholders, never interpolating user input into the query string.

**SPY as benchmark vs holding** — SPY is always fetched for Beta/benchmark computations, but only counts as a portfolio position if the user explicitly selects it.

**Shareable state in the URL** — the selected tickers, amounts, horizon, and risk-free rate are serialised into query params after each run, making any analysis a bookmarkable link.

**Native light/dark themes instead of CSS overrides** — dark mode was originally custom CSS painted over a locked light theme, targeting Streamlit's internal widget HTML. With Streamlit unpinned, Streamlit Cloud installed a newer release whose HTML no longer matched, leaving inputs half-styled with unreadable text, and every toggle re-ran the whole script. It now uses `[theme.light]` / `[theme.dark]` in `.streamlit/config.toml`, so Streamlit paints its own widgets and switching needs no rerun. The app's own cards derive their colors from `currentColor`, charts leave text and grid colors to the active theme, and Streamlit is pinned (`~=1.64.0`) so widget changes arrive deliberately.

**Tested at four levels** (151 tests) — unit tests for the metrics engine and the allocation/rebalancing logic (hand-checked values), analytic-solution tests for the optimizer, ingestion and data-validation tests that run against temporary SQLite files with a fake price source (schema creation, idempotent inserts, the refresh date window, weekend runs, bad-row rejection, split and dividend restatement, refusing a reused symbol, delisted handling), and end-to-end `streamlit.testing.AppTest` runs that execute the real app headlessly (empty state, example flow, URL prefill, custom amounts, Monte Carlo recalculation on input change). Tests are run locally; there is no CI test job yet.

**Automated refresh without committing the database** — the DB is gitignored because it's too large for GitHub (see above). A daily GitHub Actions workflow persists it between runs via `actions/cache` instead of git, and refreshes it forward with `refresh_prices.py`. Only a small `data/last_updated.json` (timestamp, ticker count, date range, row count) gets committed — that's the freshness signal any health check reads, without ever touching a large binary in git history.

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

All prices are split- and dividend-adjusted closes, so every return in the app is a total return (dividends reinvested).

**Limitations:** optimizer allocations and Monte Carlo outcomes describe the past sample, not the future — the app labels them as study aids, not recommendations. Monte Carlo assumes normally distributed returns.

**Known data limitations:**

- **Delisted tickers can't be analysed.** 14 symbols (see `tickers/delisted.csv`) have no price feed after their last trading day. Some may have been renamed rather than delisted; the S&P 500 constituents list hasn't been refreshed to pick up new symbols.
- **History for delisted tickers predates the repair.** They had no fresh download to restate from, so their stored history may still mix adjustment bases at the 2023-07-31 batch boundary (a small one-day error for dividend payers).
- **Sector labels in the exposure chart are SIC descriptions** from Massive.com, not the GICS sectors used by the sidebar filter.
- **Universe is today's S&P 500**, so long horizons carry survivorship bias: companies that left the index aren't offered.

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

# 3. Ingest price data (one-time; ~500 S&P 500 stocks + 30+ ETFs).
#    Massive's free tier is rate-limited to 5 req/min (2 calls per ticker,
#    13s sleep between calls), so a full run takes several hours. Safe to
#    interrupt and re-run — already-stored (ticker, date) rows are skipped.
python scripts/ingest_all_tickers.py

# 4. Optional: backfill history further back than step 3 reached
python scripts/backfill_history.py      # via Massive.com (slower, rate-limited)
python scripts/backfill_yfinance.py     # via yfinance (faster, fills gaps)

# 5. Keep data current (run any time; idempotent)
python scripts/refresh_prices.py

# Optional: data-quality report (duplicates, bad prices, split-like jumps, stale tickers)
python scripts/validate_data.py

# Optional: re-download and replace history (all tickers, or the ones named)
python scripts/rebuild_history.py NFLX CRWD

# 6. Run the app
python -m streamlit run streamlit_app/Portfolio_Analyzer.py

# Run the tests
python -m pytest tests/
```

---

## Automated Data Refresh (GitHub Actions)

`.github/workflows/refresh_data.yml` runs `scripts/refresh_prices.py` automatically every weekday (scheduled for 11:00 UTC; GitHub typically starts it several hours later, during US market hours, which is why today's bar is never fetched) and on manual dispatch. Since the price database is gitignored, the workflow never commits it — instead:

1. The DB is restored from **GitHub Actions cache** (persists between runs, no git history bloat).
2. `refresh_prices.py` fetches forward from each ticker's last known date through the previous day's close, restating any ticker the source has re-adjusted.
3. `scripts/write_last_updated.py` writes `data/last_updated.json` — a timestamp, ticker count, date range, and row count.
4. The updated DB is saved back to cache; `last_updated.json` is committed **only if it changed**.
5. A rolling backup of the DB is also uploaded to a GitHub Release (`data-seed` tag) — used only if the cache is ever empty (first run, or a cache eviction).
6. `scripts/validate_data.py --max-age-days 4 --recent-jump-days 30` runs last. A red run means the data needs a look: newest price more than 4 days old (enough slack for weekends and one-day holidays), a ticker stopped updating without being on the delisted list, or a split-sized move in the last 30 days.

A manual run can also tick **rebuild_history** to re-download every non-delisted ticker before refreshing.

**One-time setup:** the bootstrap fallback needs a starter DB uploaded once:

```bash
gh release create data-seed data/portfolio_data.db \
  --title "Price data seed" \
  --notes "Bootstrap fallback for the daily refresh workflow."
```

After that, the workflow is self-sufficient — no secrets beyond the default `GITHUB_TOKEN` are required. The same `data-seed` release doubles as the bootstrap source for the Streamlit Cloud deploy below, so both stay in sync automatically.

---

## Deployment (Streamlit Community Cloud)

The app is deployed at the link at the top of this README. Streamlit Cloud builds directly from this repo, but its containers have no persistent disk and the database is gitignored — so `Portfolio_Analyzer.py` checks for `data/portfolio_data.db` on startup and downloads it from the `data-seed` GitHub Release if it's missing (a few seconds, shown with a spinner). This only happens on a cold start; once running, the container reuses the same file for every visitor until it sleeps again.

No secrets are required in Streamlit Cloud's dashboard — the app never calls a live pricing API, only the public release URL.

---

## Project Structure

```
├── .github/workflows/
│   └── refresh_data.yml        # Daily automated price refresh (see above)
├── streamlit_app/
│   ├── Portfolio_Analyzer.py   # Orchestration: DB bootstrap, sidebar, session state, tabs
│   ├── allocation.py           # Budget-constrained dollar allocation for custom weighting
│   ├── charts.py               # Plotly chart builders
│   ├── insights.py             # Rule-based plain-English findings
│   ├── interpret.py            # Metric interpretations + card rendering
│   ├── style.py                # CSS for the app's own cards (theme is native)
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
│   ├── schema.py               # Table + unique-index definitions (created if missing)
│   ├── store_data.py           # Batch validation + idempotent writes (INSERT OR IGNORE)
│   ├── ingest_all_tickers.py   # Initial ingestion for S&P 500 + ETF universe
│   ├── backfill_history.py     # Extends history via Massive.com (rate-limited)
│   ├── backfill_yfinance.py    # Fills historical gaps via yfinance
│   ├── refresh_prices.py       # Forward refresh to yesterday + restatement on re-adjustment
│   ├── rebuild_history.py      # Re-download and replace history (manual repair)
│   ├── symbols.py              # Yahoo symbol format, delisted list loader
│   ├── write_last_updated.py   # Writes data/last_updated.json freshness metadata
│   ├── validate_data.py        # Data-quality report for the whole database
│   ├── utils.py                # API key loading, rate-limit sleep
│   └── .env                    # API key (git-ignored)
├── tests/
│   ├── test_core.py            # Metrics engine unit tests
│   ├── test_optimize.py        # Optimizer vs analytic solutions
│   ├── test_allocation.py      # Budget-rebalancing logic unit tests
│   ├── test_ingestion.py       # Schema, inserts, refresh window, data validation
│   └── test_app.py             # Headless end-to-end app runs (AppTest)
├── tickers/
│   ├── constituents.csv        # S&P 500 constituents with GICS sectors
│   └── delisted.csv            # Symbols kept for history but not refreshed or analysed
└── dags/
    └── data_ingestion_dag.py   # Airflow DAG scaffold (not active)
```

---

## Stack

| Layer | Technology |
|---|---|
| UI / app framework | Streamlit |
| Deployment | Streamlit Community Cloud |
| Automation | GitHub Actions (scheduled cron + manual dispatch) |
| Charts | Plotly |
| Data manipulation | pandas, NumPy |
| Database | SQLite (via `sqlite3`) |
| Initial data source | Massive.com REST API (formerly Polygon.io) |
| Backfill / daily refresh source | yfinance |
| Styling | Streamlit native light/dark themes (`config.toml`) + CSS for custom cards |
| Testing | pytest + `streamlit.testing.AppTest` |
| Language | Python 3.10+ |
