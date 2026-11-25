# Portfolio Risk Analysis

**[Live demo →](https://portfolio-risk-insights.streamlit.app/)**

An interactive portfolio risk dashboard built with Streamlit, deployed on Streamlit Community Cloud, backed by a SQLite database of historical prices from Yahoo Finance (via yfinance). Built for two audiences at once: people who want to understand what their portfolio actually does, and people learning what these metrics mean in the first place. Every number comes with a plain-English interpretation and a full glossary.

---

## What It Does

- Search and select up to 25 stocks, ETFs and mutual funds from a universe of 500+ S&P 500 constituents plus 30+ ETFs across broad market, sector, bond, dividend, real asset, and international categories, and 9 Fidelity and Vanguard index mutual funds (labelled "(mutual fund)" in the search box); SPY is always included as the market benchmark (and can also be held as a position)
- **Analyze your real portfolio**: enter the dollar amount you hold in each position, or use equal weighting to explore. Set a total portfolio value and amounts auto-balance to it. Edit one holding and the rest adjust, with a warning if an edit would exceed the total
- Filter the stock universe by GICS sector; choose a 1, 3, 5 or 10 year horizon (price history starts in January 2020, so 10 years currently shows everything available, and the summary line states the exact date range) and a risk-free rate adjustable in 0.1% steps
- **Overview tab**: scorecard vs SPY (return, volatility, Sharpe, max drawdown), seven interpreted metric cards, and automatic plain-English insights (correlation clusters, sector concentration, risk drivers, worst month, improvement opportunities)
- **Performance tab**: cumulative returns vs SPY, per-asset metrics table, sector exposure
- **Risk tab**: underwater (drawdown) chart, rolling volatility, and rolling beta, showing *when* risk showed up rather than one number for the whole period
- **Diversification tab**: 0–100 diversification score (correlation × effective positions), correlation matrix heatmap
- **What-If & Optimize tab**: approximate max-Sharpe and min-volatility reference allocations with a suggested rebalance table, an efficient frontier (2,500 random portfolios), and live weight sliders that update every metric instantly
- **Planning tab**: Monte Carlo simulation (1,000 paths) with target value and probability of reaching it, fully recalculated on every input change
- Portfolios are saved in the page URL, so you can bookmark or share a link and the analysis reloads
- Light and dark themes (switch from the ⋮ menu; follows the device by default), onboarding flow with a one-click example portfolio

---

## Architecture

```
Yahoo Finance   ──► refresh_prices.py (via yfinance) ─► SQLite (forward refresh, restatements,
                                                               new-ticker backfill, adjustment check)
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

A diagram of the full system is in docs/architecture.excalidraw (open it at excalidraw.com). It predates the move to Yahoo as the only price source and still shows the Massive.com ingestion path.

Data is ingested once and refreshed forward daily. The Streamlit app itself never calls a live pricing API; it only reads SQLite. On Streamlit Cloud, where the database can't be committed to git, the app downloads it once per cold start from the same GitHub Release the automation keeps fresh, then behaves identically to a local run.

| Module | Responsibility |
|---|---|
| `metrics/core.py` | Pure-function metric computations (Sharpe, Sortino, Beta, drawdown, VaR/CVaR, diversification score) |
| `metrics/optimize.py` | Long-only max-Sharpe / min-volatility search (iterated Dirichlet sampling, no solver dependency) |
| `streamlit_app/allocation.py` | Budget-constrained dollar allocation: locks edited holdings, auto-balances the rest to a target total |
| `streamlit_app/charts.py` | All Plotly chart builders (pure functions of data; theme-neutral so they follow light/dark) |
| `streamlit_app/insights.py` | Rule-based plain-English findings engine |
| `streamlit_app/interpret.py` | Metric interpretations, badge ranges, card rendering, table stylers |
| `streamlit_app/style.py` | CSS for the app's own HTML cards only; light/dark itself is Streamlit's native theme (`.streamlit/config.toml`) |
| `streamlit_app/Portfolio_Analyzer.py` | Orchestration: DB bootstrap, sidebar, state, tabs |
| `scripts/checks.py` | Twin-fund groups and the twin-fund and adjustment checks (warnings only) |

---

## Data

**Source.** Prices come from Yahoo Finance, through the `yfinance` library, and from nowhere else. Yahoo's data is intended for personal use; this app is a non-commercial portfolio project. Every active ticker was re-downloaded from Yahoo on 2026-10-14 (`scripts/rebuild_history.py`); the 15 delisted tickers keep their older history, part of which was loaded from Massive.com before that. Sector descriptions in the exposure chart also date from the Massive.com load.

**Universe.** Today's S&P 500 constituents (`tickers/constituents.csv`), 31 ETFs, and 9 index mutual funds (`tickers/mutual_funds.csv`): FXAIX, FSKAX, FZROX, FTIHX, FXNAX (Fidelity) and VFIAX, VTSAX, VTIAX, VBTLX (Vanguard). History starts 2020-01-02 for all of them.

**Mutual funds.** A mutual fund has one price a day, its NAV, struck after the close; an ETF trades all day and its price is the market close. Yahoo serves funds with open = high = low = close and volume 0. Nothing in the app or the pipeline uses open, high, low or volume, so they need no special handling. Two Yahoo quirks show up in the stored fund data and are left as Yahoo publishes them:

- *Stale NAVs.* On a few days Yahoo repeats a fund's previous NAV and catches up the next day. On 2025-05-07 all nine funds repeat their 05-06 price; on 2025-06-24 the four Vanguard funds do. The two-day return is right, but each single day is off by up to about 1.2%.
- *Month-end bond income.* FXNAX and VBTLX accrue income daily and pay it at month end without the NAV dropping, so Yahoo's adjusted series books the whole month's income (about 0.3%) on the last business day of the month. Total return is right; daily volatility is barely affected (VBTLX 6.05% a year over five years, BND 6.07%).

**New tickers reach production through the refresh.** The production database lives in the Actions cache, not in git. `refresh_prices.py` gives every fund in `tickers/mutual_funds.csv` a `tickers_meta` row, then downloads the full history of any ticker that has metadata but no prices. Adding a fund is a one-line change to that file; the next scheduled run backfills it.

**Checks.** `scripts/validate_data.py` runs after every refresh. Errors turn the run red; warnings are listed and, in GitHub Actions, shown as annotations on the run page, but never fail it.

| Check | Kind | What it does |
|---|---|---|
| Hard invariants | error | One row per ticker and date, a positive close, high not below low, ISO dates, nothing dated in the future, every priced ticker has metadata, the unique index exists |
| Stale tickers | error | A ticker more than 7 days behind the newest data must be listed in `tickers/delisted.csv` |
| Freshness | error (workflow) | Newest price no more than 4 days old |
| Split-sized moves | warning; error if within 30 days (workflow) | Any one-day move of 50% or more: the sign of an unadjusted split |
| Twin funds | warning | Funds that track the same index should have near-identical daily returns. Each day, a member further from its group's median than the group's limit is flagged, and the report says whether the gap reverses the next day (a late or stale price) or stays open (a missed distribution or a bad adjustment). Divergences from the last 30 days are listed; older ones are counted |
| Adjustment | warning (in the refresh) | On every ex-dividend or split date the refresh stores, the stored adjusted return must equal what Yahoo's own raw closes and dividend record imply, `raw[t] / (raw[t-1] - dividend[t]) - 1`. It uses the same download as the prices, so it costs no extra calls; every dividend restates the ticker from a full download, so each ticker's whole history is re-checked each time it pays |

The adjustment check compares Yahoo with itself. It catches a stored series that skipped or misapplied an adjustment. It cannot catch a dividend Yahoo leaves out of both its prices and its records; for funds, the twin check covers that. Across 1,686 dividend and split events (a sample of S&P 500 stocks plus the 19 grouped funds and ETFs), Yahoo's adjusted returns matched the formula to within 0.0001%, and the check's limit is 0.02%.

**Twin groups and limits.** Defined in `scripts/checks.py`, with the reason each group's members count as twins. A group's limit on a given day is its base tolerance plus 3% of the group's median move, because ETF closing prices and fund NAVs drift further apart on big days. In a two-member group each member sits half the gap from the median, so a pair catches a missed distribution of about twice its base tolerance.

| Group | Members | Base tolerance | Catches on a quiet day | Flagged days, 2020-01-02 to 2026-11-20 | Of those, in the last 250 trading days |
|---|---|---|---|---|---|
| S&P 500 | SPY, IVV, VOO, FXAIX, VFIAX | 0.15% | 0.25% | 29 | 4 |
| US total market | VTI, VTSAX, FSKAX, FZROX | 0.15% | 0.25% | 24 | 2 |
| US aggregate bonds (ETFs) | AGG, BND | 0.10% | 0.30% | 13 | 0 |
| US aggregate bonds (mutual funds) | FXNAX, VBTLX | 0.10% | 0.30% | 8 | 0 |
| Total international | FTIHX, VTIAX | 0.15% | 0.40% | 9 | 0 |

The bond ETFs and bond mutual funds are separate groups because of the month-end income above. VEA vs EFA and VWO vs EEM are not grouped: they track different index families, and their daily gaps reach 0.4% and 1% in ordinary months.

None of the historical flags is a missed distribution. Outside March and April 2020, all 84 member flags but one either reverse the next day or are the catch-up day of one that did: stale NAVs, and ETF closing prices that drift from NAV for a day (SPY closed 1% above IVV and VOO on 2025-04-09 and gave it back the next day). The one exception, IVV on 2026-07-01, closed a gap that opened on 06-26, the Russell reconstitution day; IVV's ex-date was 06-15. In March and April 2020, ETFs traded away from their NAVs for days at a time (the bond ETFs by over 1% a day), so some gaps stayed open for days; the ETF gaps had closed by mid-April. FXNAX and VBTLX came out of it about 0.2% apart, which looks like a real tracking difference between the two funds in that bond-market stress rather than a data error.

---

## Key Engineering Decisions

**Deployable without committing the database.** The price database is gitignored: about 105MB as of October 2026, over GitHub's 100MB per-file limit, and growing by roughly 525 rows every trading day (one per active ticker) (`data/last_updated.json` has the current row count). Streamlit Cloud's container starts with no local disk state, so the app checks for the database on startup and downloads it from a GitHub Release if it's missing, then proceeds exactly as it would locally. The same release is updated every weekday by the ingestion automation with prices through the previous trading day's close.

**Budget-constrained allocation, not just weights.** `allocation.py` treats a portfolio value as a real budget: editing one holding's dollar amount locks it and re-splits the remainder across the rest so the total always equals the budget, and an edit that would exceed it is rejected with a warning instead of silently accepted. Kept as pure functions so the rebalancing rules (including the exact "$5 across 4 holdings" edge case) are unit-tested independent of any UI state.

**Real weights, alignment-safe.** Portfolio functions accept `{ticker: weight}` dicts and align them to the returns matrix internally, so column ordering can never silently mismatch weights.

**Solver-free optimisation.** Max-Sharpe / min-vol weights are found by iterated Dirichlet sampling (sample the simplex, concentrate around the incumbent, repeat). Approximate but deterministic, long-only by construction, and dependency-free; validated against the two-asset analytic solution in tests.

**Diversification score with two components.** Weighted average pairwise correlation (mapped over the realistic 0–0.8 range) × effective number of positions (`1/Σw²`), so both "everything moves together" and "one position dominates" pull the score down.

**Idempotent ingestion, schema in code.** Every write goes through one function (`store_data.insert_prices`) that uses `INSERT OR IGNORE` against a `(ticker, date)` unique index, so scripts can be interrupted and re-run without duplicates. `scripts/schema.py` creates the tables and that index if they are missing, so a brand-new database gets the same guarantee. Rows are only ever overwritten through the restatement path below.

**Only complete trading days are stored.** The daily refresh fetches through yesterday and never today, and `validate_prices` rejects any row dated later than that, because a partial bar would never be corrected. yfinance's `end` date is exclusive; an earlier version passed yesterday as `end` and so ran one trading day behind on every run while the workflow stayed green. The fix is pinned by a regression test that fakes the same exclusive-end contract.

**Restate a ticker when the source re-adjusts it.** Prices are adjusted closes, and Yahoo re-adjusts a ticker's entire history every time it pays a dividend or splits. Appending new rows to old ones mixes two adjustment bases: a 10-for-1 split shows up as a −90% day. So each refresh also re-fetches the last stored day (the anchor) and compares it to what is stored. If it no longer matches, the whole ticker is replaced from a fresh download, in one transaction. Split flags from the source were not usable for this: CRWD's split is dated after the day its data broke. Replacement is refused unless the fresh history covers the stored one and its daily returns match on at least 80% of shared days, which is what stopped `PARA` (the symbol now belongs to a different security) from being overwritten. `scripts/rebuild_history.py` runs the same replacement for every ticker; it was used once to repair history that had been loaded in three differently-adjusted batches.

**Delisted tickers are kept, labelled and refused.** `tickers/delisted.csv` lists symbols with no usable price feed. Their history stays in the database and in the picker (labelled with the date their data ends), but they are not refreshed, and the app will not analyse a portfolio that holds one: past its last price a holding would be forward-filled as a flat line, quietly understating risk. The app explains which holding and why. The list is a reviewed file rather than something the pipeline infers, so one failed download never takes a ticker out of service. An optional `last_valid_date` column removes rows known to be wrong: before the restatement guard existed, the refresh appended another security's prices to `PARA` after the symbol was reused, and those rows are trimmed on every run.

**Validation as an alarm, not a gate.** `scripts/validate_data.py` checks grain, prices, date format, metadata coverage, freshness, stale tickers not on the delisted list, and split-sized one-day moves. Bad rows are already blocked before insert, so in the workflow it runs after the data is saved and turns the run red for a human to look, rather than discarding a day's data. The twin-fund and adjustment checks (see Data above) are warnings only: they are listed and annotated on the run page but never turn it red.

**One price source, checked against itself.** The database was first built from Massive.com and yfinance in batches; every active ticker has since been re-downloaded from Yahoo, which is the only source the refresh uses. A second provider was ruled out because free tiers are for personal use and this is a public site. Instead the pipeline checks Yahoo with data it already has: twin funds that must move together, and Yahoo's own raw closes and dividend records.

**Parameterized SQL with dynamic `IN` clause.** `helpers.get_price_data` builds `IN (?,?,?)` from placeholders, never interpolating user input into the query string.

**SPY as benchmark vs holding.** SPY is always fetched for Beta/benchmark computations, but only counts as a portfolio position if the user explicitly selects it.

**Shareable state in the URL.** The selected tickers, amounts, horizon, and risk-free rate are serialised into query params after each run, making any analysis a bookmarkable link.

**Native light/dark themes instead of CSS overrides.** Dark mode was originally custom CSS painted over a locked light theme, targeting Streamlit's internal widget HTML. With Streamlit unpinned, Streamlit Cloud installed a newer release whose HTML no longer matched, leaving inputs half-styled with unreadable text, and every toggle re-ran the whole script. It now uses `[theme.light]` / `[theme.dark]` in `.streamlit/config.toml`, so Streamlit paints its own widgets and switching needs no rerun. The app's own cards derive their colors from `currentColor`, charts leave text and grid colors to the active theme, and Streamlit is pinned (`~=1.64.0`) so widget changes arrive deliberately.

**Tested at four levels** (213 tests): unit tests for the metrics engine and the allocation/rebalancing logic (hand-checked values), analytic-solution tests for the optimizer, ingestion and data-validation tests that run against temporary SQLite files with a fake price source (schema creation, idempotent inserts, the refresh date window, weekend runs, bad-row rejection, split and dividend restatement, refusing a reused symbol, delisted handling, new-ticker backfill, mutual fund bars), tests of the twin-fund and adjustment checks on synthetic data (a missed dividend, a stale price, a missed split, big-move tolerance), and end-to-end `streamlit.testing.AppTest` runs that execute the real app headlessly (empty state, example flow, URL prefill, custom amounts, Monte Carlo recalculation on input change, mutual funds in search and analysis). A GitHub Actions job (`tests.yml`) runs the suite on every push to main. The 11 end-to-end app tests need the local price database, so in CI 202 run and 11 skip. Locally all 213 run; with a database that predates the mutual funds, the 2 mutual fund app tests skip.

**Automated refresh without committing the database.** The DB is gitignored because it's too large for GitHub (see above). A daily GitHub Actions workflow persists it between runs via `actions/cache` instead of git, and refreshes it forward with `refresh_prices.py`. Only a small `data/last_updated.json` (timestamp, ticker count, date range, row count) gets committed. That is the freshness signal any health check reads, and it keeps the large binary out of git history.

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

**Limitations:** optimizer allocations and Monte Carlo outcomes describe the past sample, not the future. The app labels them as study aids, not recommendations. Monte Carlo assumes normally distributed returns.

**Known data limitations:**

- **Delisted tickers can't be analysed.** 15 symbols (see `tickers/delisted.csv`) have no price feed after their last trading day. Some may have been renamed rather than delisted; the S&P 500 constituents list hasn't been refreshed to pick up new symbols.
- **History for delisted tickers predates the repair.** They had no fresh download to restate from, so their stored history may still mix adjustment bases at the 2023-07-31 batch boundary (a small one-day error for dividend payers).
- **Sector labels in the exposure chart are SIC descriptions** from Massive.com, not the GICS sectors used by the sidebar filter.
- **Mutual funds have no sector.** Like ETFs, they appear as "Other / ETF" in the sector exposure chart.
- **Universe is today's S&P 500**, so long horizons carry survivorship bias: companies that left the index aren't offered.

---

## Setup

**Prerequisites:** Python 3.10+, a Massive.com API key (free tier works; formerly Polygon.io; existing keys still work). Only steps 2 to 4 below use it: they are how the database was first built. The daily refresh needs no key.

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
#    interrupt and re-run. Already-stored (ticker, date) rows are skipped.
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

`.github/workflows/refresh_data.yml` runs `scripts/refresh_prices.py` automatically every weekday (scheduled for 11:00 UTC; GitHub typically starts it several hours later, during US market hours, which is why today's bar is never fetched) and on manual dispatch. Since the price database is gitignored, the workflow never commits it. Instead:

1. The DB is restored from **GitHub Actions cache** (persists between runs, no git history bloat).
2. `refresh_prices.py` backfills the full history of any new ticker (a fund added to `tickers/mutual_funds.csv`, or any ticker with metadata but no prices), then fetches forward from each ticker's last known date through the previous day's close, restating any ticker the source has re-adjusted and adjustment-checking what it stores.
3. `scripts/write_last_updated.py` writes `data/last_updated.json`: a timestamp, ticker count, date range, and row count.
4. The updated DB is saved back to cache; `last_updated.json` is committed **only if it changed**.
5. A rolling backup of the DB is also uploaded to a GitHub Release (`data-seed` tag), used only if the cache is ever empty (first run, or a cache eviction).
6. `scripts/validate_data.py --max-age-days 4 --recent-jump-days 30` runs last. A red run means the data needs a look: newest price more than 4 days old (enough slack for weekends and one-day holidays), a ticker stopped updating without being on the delisted list, or a split-sized move in the last 30 days. Twin-fund divergences from the last 30 days are listed as warnings and annotations without failing the run.

A manual run can also tick **rebuild_history** to re-download every non-delisted ticker before refreshing.

**One-time setup:** the bootstrap fallback needs a starter DB uploaded once:

```bash
gh release create data-seed data/portfolio_data.db \
  --title "Price data seed" \
  --notes "Bootstrap fallback for the daily refresh workflow."
```

After that, the workflow is self-sufficient: no secrets beyond the default `GITHUB_TOKEN` are required. The same `data-seed` release doubles as the bootstrap source for the Streamlit Cloud deploy below, so both stay in sync automatically.

---

## Deployment (Streamlit Community Cloud)

The app is deployed at the link at the top of this README. Streamlit Cloud builds directly from this repo, but its containers have no persistent disk and the database is gitignored, so `Portfolio_Analyzer.py` checks for `data/portfolio_data.db` on startup and downloads it from the `data-seed` GitHub Release if it's missing (a few seconds, shown with a spinner). This only happens on a cold start; once running, the container reuses the same file for every visitor until it sleeps again.

No secrets are required in Streamlit Cloud's dashboard. The app never calls a live pricing API, only the public release URL.

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
│   ├── symbols.py              # Yahoo symbol format, delisted and mutual fund list loaders
│   ├── checks.py               # Twin-fund and adjustment checks (warnings)
│   ├── write_last_updated.py   # Writes data/last_updated.json freshness metadata
│   ├── validate_data.py        # Data-quality report for the whole database
│   ├── utils.py                # API key loading, rate-limit sleep
│   └── .env                    # API key (git-ignored)
├── tests/
│   ├── test_core.py            # Metrics engine unit tests
│   ├── test_optimize.py        # Optimizer vs analytic solutions
│   ├── test_allocation.py      # Budget-rebalancing logic unit tests
│   ├── test_ingestion.py       # Schema, inserts, refresh window, backfill, data validation
│   ├── test_checks.py          # Twin-fund and adjustment checks on synthetic data
│   └── test_app.py             # Headless end-to-end app runs (AppTest)
├── tickers/
│   ├── constituents.csv        # S&P 500 constituents with GICS sectors
│   ├── delisted.csv            # Symbols kept for history but not refreshed or analysed
│   └── mutual_funds.csv        # Index mutual funds in the universe (backfilled by the refresh)
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
| Price data | Yahoo Finance via yfinance (the only price source) |
| Original ingestion and sector descriptions | Massive.com REST API (formerly Polygon.io), no longer used |
| Styling | Streamlit native light/dark themes (`config.toml`) + CSS for custom cards |
| Testing | pytest + `streamlit.testing.AppTest` |
| Language | Python 3.10+ |
