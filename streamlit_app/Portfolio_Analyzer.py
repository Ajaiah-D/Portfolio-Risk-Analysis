import datetime
import sqlite3
import sys

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, ".")
from data import helpers
from metrics import core, optimize
from streamlit_app import charts, insights, interpret, style
from streamlit_app.interpret import metric_card_html, style_asset_table, corr_cell_css

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Portfolio Risk Analysis",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state defaults ────────────────────────────────────────────────────
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

dark = st.session_state.dark_mode
style.inject_css(dark)

# ── Cached data loaders ───────────────────────────────────────────────────────
@st.cache_data
def load_universe():
    """Load S&P 500 constituents + ETF list from DB, merged with GICS sectors."""
    conn = sqlite3.connect("data/portfolio_data.db")
    db_tickers = set(
        pd.read_sql("SELECT DISTINCT ticker FROM daily_prices", conn)["ticker"]
    )
    meta = pd.read_sql("SELECT DISTINCT ticker, name FROM tickers_meta", conn)
    conn.close()
    meta_dict = dict(zip(meta["ticker"], meta["name"]))

    # S&P 500 with GICS sectors
    const = pd.read_csv("tickers/constituents.csv")[["Symbol", "Security", "GICS Sector"]]
    const = const[const["Symbol"].isin(db_tickers)].copy()
    const["label"] = const["Symbol"] + "  —  " + const["Security"]
    const = const.sort_values("Symbol").reset_index(drop=True)

    # ETFs (in DB but not S&P 500). SPY is offered too — it's always the
    # benchmark, but users can also hold it as a position.
    sp500_syms = set(const["Symbol"])
    etf_rows = []
    for sym in sorted(db_tickers - sp500_syms):
        name = meta_dict.get(sym, sym)
        label = f"{sym}  —  {name}" if name and name != sym else sym
        etf_rows.append({"symbol": sym, "label": label})
    etfs = pd.DataFrame(etf_rows)

    sectors = sorted(const["GICS Sector"].unique().tolist())
    return const, etfs, sectors


const_df, etfs_df, all_sectors = load_universe()

EQUAL_MODE = "Equal weight"
CUSTOM_MODE = "Custom amounts ($)"
_HORIZON_LABELS = {"1": "1 Year", "3": "3 Years", "5": "5 Years", "10": "10 Years"}
_HORIZON_NUMS = {v: k for k, v in _HORIZON_LABELS.items()}


def extract_symbol(label):
    return label.split("  —  ")[0].strip()


# ── URL prefill (shareable portfolios) ────────────────────────────────────────
# ?t=AAPL,MSFT&h=5&r=5&a=1000,2000 (custom $) or &v=25000 (portfolio value)
_qp = st.query_params
if "t" in _qp and not st.session_state.get("qp_loaded"):
    st.session_state.qp_loaded = True
    _syms = [s.strip().upper() for s in _qp["t"].split(",") if s.strip()]
    _sp500 = set(const_df["Symbol"])
    st.session_state["stock_sel"] = const_df[const_df["Symbol"].isin(_syms)]["label"].tolist()
    if not etfs_df.empty:
        _etf_syms = [s for s in _syms if s not in _sp500]
        st.session_state["etf_sel"] = etfs_df[etfs_df["symbol"].isin(_etf_syms)]["label"].tolist()
    st.session_state["horizon"] = _HORIZON_LABELS.get(_qp.get("h", "5"), "5 Years")
    try:
        _r = float(_qp.get("r", 5.0))
        st.session_state["rfr_pct"] = min(max(round(_r * 2) / 2, 0.0), 10.0)
    except ValueError:
        pass
    if "a" in _qp:
        _amts = _qp["a"].split(",")
        st.session_state["wmode"] = CUSTOM_MODE
        try:
            st.session_state["amounts"] = {
                s: float(a) for s, a in zip(_syms, _amts) if a
            }
        except ValueError:
            pass
    elif "v" in _qp:
        try:
            st.session_state["pv"] = int(float(_qp["v"]))
        except ValueError:
            pass
    st.session_state.analysis_run = True


# ── Example portfolio (onboarding) ────────────────────────────────────────────
def _load_example():
    ex_stocks = ["AAPL", "MSFT", "JNJ", "XOM", "PG"]
    st.session_state["stock_sel"] = const_df[const_df["Symbol"].isin(ex_stocks)]["label"].tolist()
    if not etfs_df.empty:
        st.session_state["etf_sel"] = etfs_df[etfs_df["symbol"].isin(["QQQ", "GLD"])]["label"].tolist()
    st.session_state["wmode"] = EQUAL_MODE
    st.session_state.analysis_run = True


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:

    new_dark = st.toggle("Dark mode", value=st.session_state.dark_mode, key="dark_toggle")
    if new_dark != st.session_state.dark_mode:
        st.session_state.dark_mode = new_dark
        st.rerun()

    st.markdown("---")

    st.markdown('<span class="sb-label">Time Horizon</span>', unsafe_allow_html=True)
    time_horizon = st.radio(
        "Time Horizon",
        ["1 Year", "3 Years", "5 Years", "10 Years"],
        index=2,
        key="horizon",
        label_visibility="collapsed",
    )

    st.markdown("---")

    st.markdown('<span class="sb-label">Filter by Sector</span>', unsafe_allow_html=True)
    selected_sectors = st.multiselect(
        "Filter by Sector",
        options=all_sectors,
        default=[],
        placeholder="All sectors",
        label_visibility="collapsed",
    )

    st.markdown('<span class="sb-label">Stocks</span>', unsafe_allow_html=True)
    st.caption("Search by ticker or company name.")
    if selected_sectors:
        pool = const_df[const_df["GICS Sector"].isin(selected_sectors)]
    else:
        pool = const_df
    stock_options = pool["label"].tolist()

    selected_stock_labels = st.multiselect(
        "Stocks",
        options=stock_options,
        placeholder="Type to search…",
        max_selections=25,
        key="stock_sel",
        label_visibility="collapsed",
    )

    st.markdown('<span class="sb-label">ETFs &amp; Indices</span>', unsafe_allow_html=True)
    st.caption("SPY is always the benchmark — add it here to also hold it.")
    etf_options = etfs_df["label"].tolist() if not etfs_df.empty else []
    selected_etf_labels = st.multiselect(
        "ETFs",
        options=etf_options,
        placeholder="e.g. SPY, QQQ, GLD…",
        key="etf_sel",
        label_visibility="collapsed",
    )

    # Symbols the user actually picked (their holdings)
    user_picks = [extract_symbol(l) for l in selected_stock_labels]
    user_picks += [extract_symbol(l) for l in selected_etf_labels]
    user_picks = list(dict.fromkeys(user_picks))[:29]

    st.markdown("---")

    # ── Weighting ──
    st.markdown('<span class="sb-label">Weighting</span>', unsafe_allow_html=True)
    weight_mode = st.radio(
        "Weighting",
        [EQUAL_MODE, CUSTOM_MODE],
        key="wmode",
        label_visibility="collapsed",
    )

    amounts = {}
    if weight_mode == CUSTOM_MODE and user_picks:
        _saved = st.session_state.get("amounts", {})
        _rows = pd.DataFrame(
            {"Ticker": user_picks,
             "Amount ($)": [float(_saved.get(t, 1000.0)) for t in user_picks]}
        )
        _edited = st.data_editor(
            _rows,
            hide_index=True,
            disabled=["Ticker"],
            column_config={
                "Amount ($)": st.column_config.NumberColumn(
                    "Amount ($)", min_value=0.0, step=100.0, format="$%d"
                ),
            },
            key=f"amt_editor_{'_'.join(user_picks)}",
            width="stretch",
        )
        amounts = {
            str(r["Ticker"]): float(r["Amount ($)"] or 0.0)
            for _, r in _edited.iterrows()
        }
        st.session_state["amounts"] = {**_saved, **amounts}
        st.caption(f"Total: ${sum(amounts.values()):,.0f} — metrics use these dollar weights.")
    elif weight_mode == CUSTOM_MODE:
        st.caption("Pick stocks or ETFs above to enter dollar amounts.")

    st.markdown("---")

    st.markdown('<span class="sb-label">Risk-Free Rate</span>', unsafe_allow_html=True)
    rfr_pct = st.slider(
        "Risk-Free Rate",
        min_value=0.0, max_value=10.0, value=5.0,
        step=0.5, format="%.1f%%",
        key="rfr_pct",
        label_visibility="collapsed",
    )
    rfr = rfr_pct / 100
    st.caption(f"Currently {rfr_pct:.1f}% — this is the 'safe' return (e.g. T-bill) used to measure whether your portfolio rewards you enough for the extra risk taken.")

    portfolio_value = 0
    if weight_mode == EQUAL_MODE:
        st.markdown("---")
        st.markdown('<span class="sb-label">Portfolio Value (Optional)</span>', unsafe_allow_html=True)
        portfolio_value = st.number_input(
            "Portfolio Value",
            min_value=0, max_value=100_000_000, value=0, step=1000,
            format="%d", key="pv", label_visibility="collapsed",
        )
        st.caption("Enter your total investment to translate risk percentages into dollar amounts.")

    st.markdown("---")
    run_btn = st.button("Run Analysis", width="stretch", type="primary")
    st.caption("After running, your setup is saved in the page URL — copy it from the address bar to share or bookmark.")

# ── Dates ─────────────────────────────────────────────────────────────────────
_days   = {"1 Year": 365,  "3 Years": 1095, "5 Years": 1825, "10 Years": 3650}
_buffer = {"1 Year": 60,   "3 Years": 120,  "5 Years": 150,  "10 Years": 200}
end_date   = datetime.date.today()
start_date = end_date - datetime.timedelta(days=_days[time_horizon] + _buffer[time_horizon])

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<h1 class="hero-title">Portfolio <span>Risk</span> Analysis</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="hero-sub">Understand what your portfolio actually does: how much risk you\'re taking, '
    "where it comes from, and what the same holdings could look like with different weights. "
    "Every metric is explained in plain English — see the Glossary page for definitions.</p>",
    unsafe_allow_html=True,
)

if run_btn:
    st.session_state.analysis_run = True

# ── Onboarding empty state ────────────────────────────────────────────────────
if not st.session_state.get("analysis_run", False):
    _steps = st.columns(3)
    _step_content = [
        ("1", "Pick your holdings",
         "Choose up to 25 stocks and ETFs in the sidebar — search by ticker or company name. SPY is always included as the market benchmark."),
        ("2", "Set your amounts",
         "Use equal weighting to explore, or switch to Custom amounts and enter the dollars you actually hold in each position."),
        ("3", "Run the analysis",
         "Get risk metrics with plain-English interpretations, automatic insights, and suggested weightings from the same holdings."),
    ]
    for col, (num, title, desc) in zip(_steps, _step_content):
        with col:
            st.markdown(
                f'<div class="step-card"><div class="step-num">{num}</div>'
                f'<div class="step-title">{title}</div>'
                f'<div class="step-desc">{desc}</div></div>',
                unsafe_allow_html=True,
            )
    st.markdown("<br>", unsafe_allow_html=True)
    _c1, _c2 = st.columns([1, 2.2])
    with _c1:
        st.button("Try an example portfolio →", type="primary", on_click=_load_example,
                  width="stretch")
    with _c2:
        st.caption("Loads a 7-asset mix (tech, healthcare, energy, consumer staples, QQQ, gold) so you can explore every feature immediately.")
    st.stop()

# ── Parse selections ──────────────────────────────────────────────────────────
if not user_picks:
    st.warning("Select at least one stock or ETF from the sidebar before running analysis.", icon="⚠️")
    st.stop()

tickers_list = list(dict.fromkeys(["SPY"] + user_picks))[:30]

# ── Fetch + compute ───────────────────────────────────────────────────────────
with st.spinner("Fetching data and computing metrics…"):
    try:
        df = helpers.get_price_data(tickers_list, str(start_date), str(end_date))
    except Exception as e:
        st.error(f"Failed to load price data: {e}")
        st.stop()

    actual  = df["ticker"].unique().tolist()
    missing = [t for t in tickers_list if t not in actual]
    held    = [t for t in user_picks if t in actual]

    if not held:
        st.error("None of the selected tickers have data for this period.")
        st.stop()

    # ── Weights: the user's actual portfolio ──
    if weight_mode == CUSTOM_MODE and sum(amounts.get(t, 0) for t in held) > 0:
        _total = sum(amounts.get(t, 0.0) for t in held)
        weights_map = {t: amounts.get(t, 0.0) / _total for t in held}
        portfolio_value = int(round(_total))
        weighting_desc = "Custom ($ amounts)"
    else:
        weights_map = {t: 1.0 / len(held) for t in held}
        weighting_desc = f"Equal ({100 / len(held):.0f}% each)"
    full_weights = {**{t: 0.0 for t in actual}, **weights_map}

    asset_df = core.compute_asset_metrics(df, benchmark_ticker="SPY", risk_free_rate=rfr)
    port_dict, corr = core.compute_portfolio_metrics(
        df, full_weights, benchmark_ticker="SPY", risk_free_rate=rfr
    )
    div_score = core.diversification_score(corr, weights_map)

    returns_wide  = df.pivot(index="date", columns="ticker", values="close").ffill().pct_change(fill_method=None).dropna(how="all")
    port_r_series = core.portfolio_return_series(returns_wide, full_weights)
    bench_r       = returns_wide["SPY"]

    sector_map = df.drop_duplicates("ticker").set_index("ticker")["sector"].to_dict()

    # ── Optimizer + insights ──
    opt = None
    if len(held) >= 2:
        opt = optimize.optimize_portfolios(returns_wide[held], rfr=rfr)
    cur_stats = optimize.portfolio_stats(returns_wide[held], weights_map, rfr=rfr)

    insight_items = insights.generate_insights(
        corr=corr,
        weights_map=weights_map,
        sector_map=sector_map,
        returns_wide=returns_wide,
        port_r=port_r_series,
        bench_r=bench_r,
        port_metrics=port_dict,
        div_score=div_score,
        opt=opt,
    )

# ── Persist setup in the URL (share / bookmark) ───────────────────────────────
_qp_out = {"t": ",".join(held), "h": _HORIZON_NUMS[time_horizon], "r": f"{rfr_pct:g}"}
if weight_mode == CUSTOM_MODE and amounts:
    _qp_out["a"] = ",".join(str(int(amounts.get(t, 0))) for t in held)
elif portfolio_value:
    _qp_out["v"] = str(int(portfolio_value))
try:
    st.query_params.from_dict(_qp_out)
except Exception:
    pass

# ── Info bar ──────────────────────────────────────────────────────────────────
chips = " ".join(
    f'<span class="chip {"chip-bench" if t == "SPY" and t not in held else ""}">{t}'
    + (f' {weights_map[t]*100:.0f}%' if t in held and len(held) > 1 else "")
    + "</span>"
    for t in actual
)
st.markdown(
    f'<div class="info-bar">'
    f"<b>Portfolio</b> &nbsp; {chips} <br>"
    f"<b>Period</b> &nbsp; {start_date} → {end_date} &nbsp;&nbsp;"
    f"<b>Horizon</b> &nbsp; {time_horizon} &nbsp;&nbsp;"
    f"<b>Risk-free rate</b> &nbsp; {rfr * 100:.1f}% &nbsp;&nbsp;"
    f"<b>Weighting</b> &nbsp; {weighting_desc}"
    f"</div>",
    unsafe_allow_html=True,
)
if missing:
    st.warning(
        f"No data found for: **{', '.join(missing)}**. Only tickers with data are shown.",
        icon="⚠️",
    )

# ── Shared stats for scorecard ────────────────────────────────────────────────
_port_total = float((1 + port_r_series.dropna()).prod() - 1)
_spy_total  = float((1 + bench_r.dropna()).prod() - 1)
_port_vol   = float(port_r_series.std() * np.sqrt(252))
_spy_vol    = float(bench_r.std() * np.sqrt(252))
_max_dd     = port_dict.get("MaxDrawdown", np.nan)


def _scard(label, value, sub="", cls=""):
    return (
        f'<div class="scard"><div class="scard-label">{label}</div>'
        f'<div class="scard-val {cls}">{value}</div>'
        f'<div class="scard-sub">{sub}</div></div>'
    )


def _section(title, heading, desc):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-heading">{heading}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-desc">{desc}</div>', unsafe_allow_html=True)


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_overview, tab_perf, tab_risk, tab_div, tab_whatif, tab_plan = st.tabs(
    ["Overview", "Performance", "Risk", "Diversification", "What-If & Optimize", "Planning"]
)

# ═══ OVERVIEW ═════════════════════════════════════════════════════════════════
with tab_overview:
    _section("At a Glance", "Portfolio vs. Market",
             "How your portfolio performed against simply holding SPY over the same period.")

    _sc = st.columns(4)
    _ret_cls = "pos" if _port_total >= _spy_total else "neg"
    _vol_cls = "pos" if _port_vol <= _spy_vol else "neg"
    _sharpe_v = port_dict.get("Sharpe", np.nan)
    _, _sharpe_word, _ = interpret.interpret_sharpe(_sharpe_v)
    _dd_sub = (f"−${abs(_max_dd) * portfolio_value:,.0f} on ${portfolio_value:,.0f}"
               if portfolio_value else "worst peak-to-trough drop")
    _cards = [
        ("Total Return", f"{_port_total*100:+.1f}%", f"SPY: {_spy_total*100:+.1f}%", _ret_cls),
        ("Volatility (Ann.)", f"{_port_vol*100:.1f}%", f"SPY: {_spy_vol*100:.1f}%", _vol_cls),
        ("Sharpe Ratio", f"{_sharpe_v:.2f}" if not pd.isna(_sharpe_v) else "—", _sharpe_word, ""),
        ("Max Drawdown", f"{_max_dd*100:.1f}%" if not pd.isna(_max_dd) else "—", _dd_sub, ""),
    ]
    for col, (lbl, val, sub, cls) in zip(_sc, _cards):
        with col:
            st.markdown(_scard(lbl, val, sub, cls), unsafe_allow_html=True)

    if insight_items:
        _section("Insights", "What Stands Out",
                 "Automatic findings from your portfolio's data — concentration, correlation, history, and improvement opportunities.")
        for item in insight_items:
            st.markdown(insights.insight_html(item), unsafe_allow_html=True)

    _section("Combined View", "Portfolio Metrics",
             "Your holdings treated as a single weighted position. These figures describe how the portfolio behaves as a whole.")
    _metric_keys = ["Sharpe", "Sortino", "Beta", "MaxDrawdown", "VaR", "CVaR", "DivScore"]
    _metric_vals = {**port_dict, "DivScore": div_score}
    cols = st.columns(3)
    for i, key in enumerate(_metric_keys):
        with cols[i % 3]:
            st.markdown(metric_card_html(key, _metric_vals.get(key, np.nan)), unsafe_allow_html=True)

    # Dollar drawdown translation
    if portfolio_value and portfolio_value > 0 and not pd.isna(_max_dd):
        _ann_ret = float(port_r_series.mean() * 252)
        _dollar_loss = abs(_max_dd * portfolio_value)
        if _ann_ret > 0 and _max_dd < 0:
            _recovery_needed = 1 / (1 + _max_dd) - 1
            _recovery_months = (np.log(1 + _recovery_needed) / np.log(1 + _ann_ret)) * 12
            _recovery_txt = f"At the portfolio's historical average annual return of <b>{_ann_ret*100:.1f}%</b>, estimated recovery is <b>~{_recovery_months:.0f} months</b>."
        else:
            _recovery_txt = "Recovery time cannot be estimated — the portfolio's historical average annual return is negative or zero."
        st.markdown(
            f'<div class="info-bar">'
            f"<b>Dollar Context</b> &nbsp; Based on a <b>${portfolio_value:,.0f}</b> portfolio &nbsp;&mdash;&nbsp; "
            f"the max drawdown of <b>{_max_dd*100:.1f}%</b> represents a peak loss of <b>${_dollar_loss:,.0f}</b>. &nbsp;"
            f"{_recovery_txt}"
            f"</div>",
            unsafe_allow_html=True,
        )

# ═══ PERFORMANCE ══════════════════════════════════════════════════════════════
with tab_perf:
    _section("Performance", "Cumulative Returns",
             "Growth of the period. The bold line is your weighted portfolio, the dotted line is SPY. Hover to compare values.")
    st.plotly_chart(charts.build_cumulative_chart(df, weights_map, dark=dark), width="stretch", key="ch_cum")

    _section("Breakdown", "Asset Metrics",
             "Per-holding risk and return over the selected period. SPY is the benchmark — Beta, Sharpe, and Sortino are measured relative to it. "
             "Green = favorable &nbsp;·&nbsp; Amber = neutral &nbsp;·&nbsp; Rose = elevated risk.")
    st.dataframe(style_asset_table(asset_df), width="stretch")

    _section("Composition", "Sector Exposure",
             "Where your money sits across GICS sectors, using your current weights. ETFs and funds without a sector are grouped as Other / ETF.")
    st.plotly_chart(charts.build_sector_chart(df, weights_map, dark=dark), width="stretch", key="ch_sector_perf")

# ═══ RISK ═════════════════════════════════════════════════════════════════════
with tab_risk:
    _section("Drawdowns", "Underwater Chart",
             "How far below its previous peak the portfolio was at every point in time. "
             "Depth shows how bad losses got; width shows how long recovery took.")
    st.plotly_chart(charts.build_underwater_chart(port_r_series, dark=dark), width="stretch", key="ch_underwater")

    _rc1, _rc2 = st.columns(2)
    with _rc1:
        _section("Volatility Over Time", "Rolling Volatility",
                 "Risk isn't constant — this shows when your portfolio was calm and when it was turbulent, vs SPY.")
        st.plotly_chart(charts.build_rolling_vol_chart(port_r_series, bench_r, dark=dark), width="stretch", key="ch_rvol")
    with _rc2:
        _section("Market Sensitivity", "Rolling Beta",
                 "How strongly your portfolio tracked the market over time. Above 1 = amplifies market moves; below 1 = defensive.")
        st.plotly_chart(charts.build_rolling_beta_chart(port_r_series, bench_r, dark=dark), width="stretch", key="ch_rbeta")

# ═══ DIVERSIFICATION ══════════════════════════════════════════════════════════
with tab_div:
    _section("Diversification", "How Independent Are Your Holdings?",
             "Diversification only works when holdings don't all move together. "
             "The score combines average correlation between your holdings with how evenly your money is spread.")
    _dc1, _dc2 = st.columns([1, 2])
    with _dc1:
        st.markdown(metric_card_html("DivScore", div_score), unsafe_allow_html=True)
        _n_eff = core.effective_holdings(list(weights_map.values()))
        st.markdown(
            f'<div class="info-bar"><b>Effective positions</b> &nbsp; Your {len(held)} holdings '
            f"behave like <b>~{_n_eff:.1f}</b> independent positions once weights are accounted for.</div>",
            unsafe_allow_html=True,
        )
    with _dc2:
        st.plotly_chart(charts.build_sector_chart(df, weights_map, dark=dark), width="stretch", key="ch_sector_div")

    _section("Correlations", "Correlation Matrix",
             "How closely each holding moves with the others. "
             "<b style='color:#10b981'>Near 0 or negative</b> = independent or inverse moves (good diversification). "
             "<b style='color:#f43f5e'>Near 1.0</b> = move together (lower diversification).")
    st.dataframe(
        corr.style.map(corr_cell_css).format("{:.2f}"),
        width="stretch",
    )

# ═══ WHAT-IF & OPTIMIZE ═══════════════════════════════════════════════════════
with tab_whatif:
    if opt is not None:
        _section("Optimizer", "What the Same Holdings Could Do",
                 "Two reference allocations found from your holdings' history: the mix that maximised risk-adjusted return (Max Sharpe), "
                 "and the mix that minimised volatility (Min Volatility). "
                 "<b>These describe the past, not the future</b> — treat them as a study aid, not advice.")

        _oc = st.columns(3)
        _opt_rows = [
            ("Your Portfolio", cur_stats, ""),
            ("Max Sharpe", opt["max_sharpe"], "bg"),
            ("Min Volatility", opt["min_vol"], "bb"),
        ]
        for col, (lbl, s, cls) in zip(_oc, _opt_rows):
            with col:
                st.markdown(
                    _scard(lbl,
                           f"Sharpe {s['sharpe']:.2f}" if not pd.isna(s["sharpe"]) else "—",
                           f"Return {s['ret']*100:.1f}% · Vol {s['vol']*100:.1f}%",
                           cls),
                    unsafe_allow_html=True,
                )

        _reb = pd.DataFrame({
            "Current": {t: weights_map.get(t, 0.0) for t in held},
            "Max Sharpe": opt["max_sharpe"]["weights"],
            "Min Volatility": opt["min_vol"]["weights"],
        }).loc[held]
        _reb["Shift to Max Sharpe"] = _reb["Max Sharpe"] - _reb["Current"]
        st.dataframe(
            _reb.style.format("{:+.1%}", subset=["Shift to Max Sharpe"])
                .format("{:.1%}", subset=["Current", "Max Sharpe", "Min Volatility"])
                .map(lambda v: "color: #10b981" if v > 0.005 else ("color: #f43f5e" if v < -0.005 else "color: #888888"),
                     subset=["Shift to Max Sharpe"]),
            width="stretch",
        )

    _section("Risk vs. Return", "Efficient Frontier",
             "Each dot is one of 2,500 randomly weighted combinations of your holdings, coloured by Sharpe ratio (pink = higher). "
             "The star is your portfolio; the green and violet markers are the optimizer's reference mixes. "
             "Portfolios toward the <b>upper-left</b> are best — higher return for less risk.")
    _opt_points = None
    if opt is not None:
        _opt_points = {
            "Max Sharpe": (opt["max_sharpe"]["vol"] * 100, opt["max_sharpe"]["ret"] * 100),
            "Min Volatility": (opt["min_vol"]["vol"] * 100, opt["min_vol"]["ret"] * 100),
        }
    frontier_fig = charts.build_frontier_chart(df, weights_map, rfr=rfr, dark=dark, opt_points=_opt_points)
    if frontier_fig:
        st.plotly_chart(frontier_fig, width="stretch", key="ch_frontier")
    else:
        st.info("Select at least 2 holdings to see the efficient frontier.", icon="ℹ️")

    # ── What-if sliders ──
    _section("What-If", "Adjust Portfolio Weights",
             "Drag the sliders to try different allocations. Metrics and sector breakdown update instantly. "
             "Weights are normalised automatically — the total always equals 100%.")

    def _apply_slider_weights(wmap):
        for t in held:
            st.session_state[f"cw_{t}"] = round(float(wmap.get(t, 0.0)) * 100, 1)

    _bc1, _bc2, _bc3, _ = st.columns([1, 1, 1, 1.4])
    _bc1.button("Reset to current", on_click=_apply_slider_weights, args=(weights_map,),
                width="stretch")
    if opt is not None:
        _bc2.button("Apply Max Sharpe", on_click=_apply_slider_weights,
                    args=(opt["max_sharpe"]["weights"],), width="stretch")
        _bc3.button("Apply Min Volatility", on_click=_apply_slider_weights,
                    args=(opt["min_vol"]["weights"],), width="stretch")

    _w_cols = st.columns(min(len(held), 4))
    _raw_w = {}
    for i, ticker in enumerate(sorted(held)):
        _default = round(float(weights_map.get(ticker, 0.0)) * 100, 1)
        _raw_w[ticker] = _w_cols[i % len(_w_cols)].slider(
            ticker, 0.0, 100.0, _default, 1.0, key=f"cw_{ticker}"
        )

    _total_w = sum(_raw_w.values())
    if _total_w > 0:
        _slider_weights = {t: _raw_w.get(t, 0.0) / _total_w for t in held}
        _slider_full = {**{t: 0.0 for t in actual}, **_slider_weights}
        _custom_port_dict, _ = core.compute_portfolio_metrics(
            df, _slider_full, benchmark_ticker="SPY", risk_free_rate=rfr
        )
        _custom_vals = {**_custom_port_dict,
                        "DivScore": core.diversification_score(corr, _slider_weights)}

        eff_chips = " ".join(
            f'<span class="chip">{t} {v*100:.1f}%</span>'
            for t, v in sorted(_slider_weights.items(), key=lambda x: -x[1])
        )
        st.markdown(
            f'<div class="info-bar"><b>Effective weights</b> &nbsp; {eff_chips}</div>',
            unsafe_allow_html=True,
        )

        _adj_cols = st.columns(3)
        for i, key in enumerate(_metric_keys):
            with _adj_cols[i % 3]:
                st.markdown(
                    metric_card_html(key, _custom_vals.get(key, np.nan)),
                    unsafe_allow_html=True,
                )

        st.plotly_chart(
            charts.build_sector_chart(df, _slider_weights, dark=dark),
            width="stretch", key="ch_sector_whatif",
        )

# ═══ PLANNING ═════════════════════════════════════════════════════════════════
with tab_plan:
    _section("Planning", "Monte Carlo Simulation",
             "Simulates 1,000 possible futures for your portfolio based on its historical daily return and volatility. "
             "Useful for understanding the range of outcomes — not a prediction. "
             "<b>Assumes normally distributed returns</b> based on past data, which underestimates extreme events.")

    if not (portfolio_value and portfolio_value > 0):
        st.info(
            "Enter your portfolio value in the sidebar (or switch to Custom amounts) to enable the Monte Carlo simulation.",
            icon="ℹ️",
        )
    else:
        _mc_col1, _mc_col2 = st.columns(2)
        with _mc_col1:
            _target_value = st.number_input(
                "Target portfolio value ($)",
                min_value=int(portfolio_value),
                max_value=100_000_000,
                value=int(portfolio_value * 2),
                step=1000,
                format="%d",
            )
        with _mc_col2:
            _mc_years = st.slider("Time horizon (years)", 1, 30, 10)

        _mc_fig, _prob, _med, _p10, _p90 = charts.build_monte_carlo(
            port_r_series, portfolio_value, _target_value, _mc_years, dark=dark
        )
        st.plotly_chart(_mc_fig, width="stretch", key="ch_mc")

        _prob_cls = "bg" if _prob >= 0.6 else ("by" if _prob >= 0.35 else "br")
        _prob_badge = f"<span class='mcard-badge {_prob_cls}'>{_prob*100:.0f}% probability</span>"
        st.markdown(
            f'<div class="info-bar">'
            f"{_prob_badge} &nbsp; of reaching <b>${_target_value:,.0f}</b> within <b>{_mc_years} years</b> &nbsp;&mdash;&nbsp; "
            f"Median outcome: <b>${_med:,.0f}</b> &nbsp;·&nbsp; "
            f"10th %ile: <b>${_p10:,.0f}</b> &nbsp;·&nbsp; "
            f"90th %ile: <b>${_p90:,.0f}</b>"
            f"</div>",
            unsafe_allow_html=True,
        )
