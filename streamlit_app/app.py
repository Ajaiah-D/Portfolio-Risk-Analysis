import streamlit as st
import datetime
import sqlite3
import pandas as pd
import numpy as np
import sys
import plotly.graph_objects as go

sys.path.insert(0, ".")
from data import helpers
from metrics import core

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

# ── CSS variables (swapped by dark mode) ─────────────────────────────────────
if dark:
    _vars = """
    --bg:      #0c0c0c;
    --bg2:     #141414;
    --bg3:     #1c1c1c;
    --text:    #f0f0f0;
    --text2:   #888888;
    --border:  #272727;
    --card:    #141414;
    --shadow:  rgba(0,0,0,0.35);
    """
else:
    _vars = """
    --bg:      #ffffff;
    --bg2:     #f7f7f7;
    --bg3:     #eeeeee;
    --text:    #111111;
    --text2:   #666666;
    --border:  #e5e5e5;
    --card:    #ffffff;
    --shadow:  rgba(0,0,0,0.06);
    """

st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {{ {_vars}
    --pink:       #fc88e5;
    --pink-dim:   rgba(252,136,229,0.12);
    --good:       #10b981;
    --good-dim:   rgba(16,185,129,0.13);
    --warn:       #f59e0b;
    --warn-dim:   rgba(245,158,11,0.13);
    --risk:       #f43f5e;
    --risk-dim:   rgba(244,63,94,0.13);
    --neutral:    #8b8cf8;
    --neutral-dim:rgba(139,140,248,0.13);
}}

html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
#MainMenu, footer {{ visibility: hidden; }}
.block-container {{ padding-top: 2rem; padding-bottom: 3rem; max-width: 1200px; }}

/* ── Global text colour (follows theme) ── */
p, span, label, div, h1, h2, h3, h4, li, caption,
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p,
[data-testid="stMarkdownContainer"] p,
.stMarkdown p,
.stRadio label, .stRadio span,
.stCheckbox label, .stCheckbox span,
.stSelectbox label,
.stMultiSelect label,
.stSlider label,
.stTextInput label,
.stCaption,
[data-testid="stCaptionContainer"] p {{
    color: var(--text) !important;
}}

/* ── Sidebar widget backgrounds & inputs ── */
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea,
[data-baseweb="input"],
[data-baseweb="textarea"],
[data-baseweb="select"] div,
[data-baseweb="popover"] li,
[data-testid="stMultiSelect"] [data-baseweb="tag"] {{
    background-color: var(--bg3) !important;
    color: var(--text) !important;
}}

/* ── Multiselect dropdown list ── */
[data-baseweb="menu"],
[data-baseweb="menu"] li,
[data-baseweb="popover"],
[role="listbox"],
[role="option"] {{
    background-color: var(--bg2) !important;
    color: var(--text) !important;
}}
[role="option"]:hover {{
    background-color: var(--bg3) !important;
}}

/* ── Multiselect tags ── */
[data-testid="stMultiSelect"] span[data-baseweb="tag"] {{
    background-color: var(--pink-dim) !important;
    color: var(--pink) !important;
}}
[data-testid="stMultiSelect"] span[data-baseweb="tag"] span {{
    color: var(--pink) !important;
}}

/* ── Radio buttons ── */
[data-testid="stRadio"] div[role="radiogroup"] label {{
    color: var(--text) !important;
}}

/* ── Slider track label & value ── */
[data-testid="stSlider"] div[data-testid="stTickBarMin"],
[data-testid="stSlider"] div[data-testid="stTickBarMax"],
[data-testid="stSlider"] p {{
    color: var(--text2) !important;
}}

/* ── Info / warning banners ── */
[data-testid="stAlert"] p {{
    color: var(--text) !important;
}}

/* ── App background ── */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > section {{
    background-color: var(--bg) !important;
}}

/* ── Top toolbar bar ── */
[data-testid="stHeader"],
.stAppHeader,
header[data-testid="stHeader"] {{
    background-color: var(--bg) !important;
    border-bottom: 1px solid var(--border) !important;
}}

/* ── Toolbar buttons visibility in dark mode ── */
[data-testid="stHeader"] button,
[data-testid="stHeader"] a,
[data-testid="stToolbar"] button,
[data-testid="stToolbar"] svg {{
    color: var(--text) !important;
    fill: var(--text) !important;
    opacity: 1 !important;
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background-color: var(--bg2) !important;
    border-right: 1px solid var(--border);
}}

/* ── Typography ── */
.hero-title {{
    font-size: 2rem; font-weight: 700; color: var(--text);
    letter-spacing: -0.5px; margin: 0 0 0.35rem 0;
}}
.hero-title span {{ color: var(--pink); }}
.hero-sub {{
    font-size: 0.9rem; color: var(--text2);
    margin: 0 0 1.8rem 0; line-height: 1.6;
}}

/* ── Section headers ── */
.section-title {{
    font-size: 0.72rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em;
    color: var(--pink);
    margin: 2.4rem 0 0.25rem 0;
}}
.section-heading {{
    font-size: 1.05rem; font-weight: 600; color: var(--text);
    margin: 0 0 0.3rem 0;
}}
.section-desc {{
    font-size: 0.8rem; color: var(--text2);
    margin: 0 0 1.1rem 0; line-height: 1.55;
}}
hr.section-rule {{
    border: none; border-top: 1px solid var(--border); margin: 0.5rem 0 1.2rem 0;
}}

/* ── Info bar ── */
.info-bar {{
    background: var(--bg2);
    border: 1px solid var(--border);
    border-left: 3px solid var(--pink);
    border-radius: 10px;
    padding: 0.85rem 1.15rem;
    margin-bottom: 1.6rem;
    font-size: 0.82rem; color: var(--text2); line-height: 1.8;
}}
.info-bar b {{ color: var(--text); font-weight: 600; }}

/* ── Chips ── */
.chip {{
    display: inline-block;
    background: var(--bg3); border: 1px solid var(--border);
    border-radius: 5px; padding: 0.12rem 0.5rem;
    font-size: 0.75rem; font-weight: 600; color: var(--text2); margin: 0.1rem;
}}
.chip-bench {{
    background: var(--pink-dim); border-color: var(--pink); color: var(--pink);
}}

/* ── Metric cards ── */
.mcard {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.1rem 1.2rem;
    box-shadow: 0 1px 4px var(--shadow);
    margin-bottom: 0.55rem;
}}
.mcard-label {{
    font-size: 0.67rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em;
    color: var(--text2); margin-bottom: 0.3rem;
}}
.mcard-val {{
    font-size: 1.75rem; font-weight: 700; color: var(--text);
    line-height: 1; margin-bottom: 0.4rem;
}}
.mcard-badge {{
    display: inline-block; padding: 0.15rem 0.55rem;
    border-radius: 20px; font-size: 0.67rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.5rem;
}}
.bg {{ background: var(--good-dim);    color: var(--good);    }}
.by {{ background: var(--warn-dim);    color: var(--warn);    }}
.br {{ background: var(--risk-dim);    color: var(--risk);    }}
.bb {{ background: var(--neutral-dim); color: var(--neutral); }}
.bp {{ background: var(--pink-dim);    color: var(--pink);    }}

.mcard-rule {{ border: none; border-top: 1px solid var(--border); margin: 0.5rem 0; }}
.mcard-desc {{ font-size: 0.77rem; color: var(--text2); line-height: 1.45; }}
.mcard-ranges {{
    font-size: 0.68rem; color: var(--text2); opacity: 0.75;
    margin-top: 0.5rem; padding-top: 0.45rem;
    border-top: 1px dashed var(--border);
    line-height: 1.55;
}}

/* ── Sidebar label style ── */
.sb-label {{
    font-size: 0.7rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.09em;
    color: var(--text2); margin-bottom: 0.25rem; display: block;
}}
</style>
""",
    unsafe_allow_html=True,
)

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

    # ETFs (in DB but not S&P 500)
    sp500_syms = set(const["Symbol"])
    etf_rows = []
    for sym in sorted(db_tickers - sp500_syms - {"SPY"}):
        name = meta_dict.get(sym, sym)
        label = f"{sym}  —  {name}" if name and name != sym else sym
        etf_rows.append({"symbol": sym, "label": label})
    etfs = pd.DataFrame(etf_rows)

    sectors = sorted(const["GICS Sector"].unique().tolist())
    return const, etfs, sectors


PCT_METRICS = {"MaxDrawdown", "VaR", "CVaR"}

# ── Interpretation logic ──────────────────────────────────────────────────────
def interpret_sharpe(v):
    if pd.isna(v): return "bb", "Benchmark", "SPY is used as the market benchmark."
    if v >= 2.0:   return "bg", "Exceptional", "Returns far exceed the risk taken — rare and highly desirable."
    if v >= 1.0:   return "bg", "Strong", "Each unit of risk is well compensated. Above 1 is considered solid."
    if v >= 0.5:   return "by", "Acceptable", "Moderate returns relative to volatility — room to improve."
    if v >= 0.0:   return "by", "Weak", "Returns barely compensate for the risk being taken."
    return "br", "Negative", "Losing value relative to the risk-free rate — risk goes unrewarded."

def interpret_sortino(v):
    if pd.isna(v): return "bb", "Benchmark", "SPY is used as the market benchmark."
    if v >= 2.0:   return "bg", "Excellent", "Strong gains with tightly controlled downside moves."
    if v >= 1.0:   return "bg", "Good", "Upward potential clearly outweighs downside volatility."
    if v >= 0.5:   return "by", "Moderate", "Some downside exposure — manageable but worth watching."
    if v >= 0.0:   return "by", "Limited", "Gains barely outpace downside volatility."
    return "br", "High Risk", "Downside losses dominate — portfolio hit hard on bad days."

def interpret_beta(v):
    if pd.isna(v): return "bb", "Benchmark", "Beta is 1.0 by definition for SPY."
    if v < 0:      return "bp", "Inverse", "Moves opposite the market — acts as a partial hedge."
    if v < 0.5:    return "bg", "Very Defensive", "Low market sensitivity — largely independent of swings."
    if v < 0.8:    return "bg", "Defensive", "Less volatile than the broader market."
    if v <= 1.2:   return "by", "Market-Like", "Tracks the market closely. Typical for large-cap US stocks."
    if v <= 1.5:   return "by", "Aggressive", "Amplifies market moves — bigger upside and steeper drops."
    return "br", "Very Aggressive", "Highly sensitive to market swings. Expect magnified gains and losses."

def interpret_drawdown(v):
    if pd.isna(v): return "bb", "N/A", ""
    if v > -0.05:  return "bg", "Minimal", "Less than 5% peak-to-trough — very resilient over this period."
    if v > -0.15:  return "bg", "Low", "Max drop stayed below 15% — reasonable drawdown resilience."
    if v > -0.25:  return "by", "Moderate", "Dropped up to 25% from peak. Worth monitoring in corrections."
    if v > -0.40:  return "by", "Severe", "Significant losses from peak — high-volatility holding."
    return "br", "Extreme", "Lost over 40% from its high — very high risk of deep losses."

def interpret_var(v):
    if pd.isna(v): return "bb", "N/A", ""
    pct = abs(v) * 100
    if pct < 1.5:  return "bg", "Low", "On a bad day (bottom 5%), expected daily loss is under 1.5%."
    if pct < 2.5:  return "by", "Moderate", f"Worst days can see around {pct:.1f}% lost in a single session."
    if pct < 3.5:  return "by", "Elevated", f"Tail risk is elevated — worst days up to {pct:.1f}% lost."
    return "br", "High", f"Up to {pct:.1f}% can be lost on the worst days — significant daily tail risk."

def interpret_cvar(v):
    if pd.isna(v): return "bb", "N/A", ""
    pct = abs(v) * 100
    if pct < 2.0:  return "bg", "Low", f"Average loss across the worst 5% of days is only {pct:.1f}%."
    if pct < 3.0:  return "by", "Moderate", f"Average worst-case daily loss is {pct:.1f}% — within range."
    if pct < 4.5:  return "by", "Elevated", f"Average loss on worst days is {pct:.1f}%. Worth hedging."
    return "br", "Severe", f"Average worst-case loss of {pct:.1f}% — heavy tail exposure."

INTERPRETERS = {
    "Sharpe": interpret_sharpe, "Sortino": interpret_sortino,
    "Beta": interpret_beta, "MaxDrawdown": interpret_drawdown,
    "VaR": interpret_var, "CVaR": interpret_cvar,
}
METRIC_DISPLAY = {
    "Sharpe": "Sharpe Ratio", "Sortino": "Sortino Ratio", "Beta": "Beta",
    "MaxDrawdown": "Max Drawdown", "VaR": "Value at Risk (5%)", "CVaR": "CVaR / Exp. Shortfall",
}
METRIC_RANGES = {
    "Sharpe":
        "< 0 = negative &nbsp;·&nbsp; 0–0.5 = weak &nbsp;·&nbsp; 0.5–1 = acceptable &nbsp;·&nbsp; > 1 = strong &nbsp;·&nbsp; > 2 = exceptional",
    "Sortino":
        "< 0 = poor &nbsp;·&nbsp; 0–0.5 = limited &nbsp;·&nbsp; 0.5–1 = moderate &nbsp;·&nbsp; > 1 = good &nbsp;·&nbsp; > 2 = excellent",
    "Beta":
        "< 0 = inverse &nbsp;·&nbsp; 0–0.5 = very defensive &nbsp;·&nbsp; 0.8–1.2 = market-like &nbsp;·&nbsp; > 1.5 = very aggressive",
    "MaxDrawdown":
        "> −5% = minimal &nbsp;·&nbsp; −5 to −15% = low &nbsp;·&nbsp; −15 to −25% = moderate &nbsp;·&nbsp; −25 to −40% = severe &nbsp;·&nbsp; < −40% = extreme",
    "VaR":
        "Daily worst-case (5th pct): < 1.5% = low &nbsp;·&nbsp; 1.5–2.5% = moderate &nbsp;·&nbsp; 2.5–3.5% = elevated &nbsp;·&nbsp; > 3.5% = high",
    "CVaR":
        "Avg loss on worst days: < 2% = low &nbsp;·&nbsp; 2–3% = moderate &nbsp;·&nbsp; 3–4.5% = elevated &nbsp;·&nbsp; > 4.5% = severe",
}

# ── Render a portfolio metric card ────────────────────────────────────────────
def metric_card_html(key, value):
    label = METRIC_DISPLAY.get(key, key)
    cls, badge, desc = INTERPRETERS[key](value)
    val_str = "—" if pd.isna(value) else (
        f"{value * 100:.2f}%" if key in PCT_METRICS else f"{value:.3f}"
    )
    ranges = METRIC_RANGES.get(key, "")
    ranges_html = f'<div class="mcard-ranges">{ranges}</div>' if ranges else ""
    return (
        f'<div class="mcard">'
        f'  <div class="mcard-label">{label}</div>'
        f'  <div class="mcard-val">{val_str}</div>'
        f'  <span class="mcard-badge {cls}">{badge}</span>'
        f'  <hr class="mcard-rule"/>'
        f'  <div class="mcard-desc">{desc}</div>'
        f'  {ranges_html}'
        f'</div>'
    )

# ── Asset table styling ───────────────────────────────────────────────────────
def _c(v, good_thresh, warn_thresh, invert=False):
    if pd.isna(v): return "color: #8b8cf8"
    cmp = -v if invert else v
    if cmp >= good_thresh: return "color: #10b981; font-weight: 600"
    if cmp >= warn_thresh: return "color: #f59e0b"
    return "color: #f43f5e"

def col_beta(v):
    if pd.isna(v): return "color: #8b8cf8"
    if 0.8 <= v <= 1.2: return "color: #f59e0b"
    if v < 0.8:         return "color: #10b981; font-weight: 600"
    if v <= 1.5:        return "color: #f59e0b"
    return "color: #f43f5e"

def corr_cell_css(v):
    if pd.isna(v): return ""
    if v >= 0.8:  return "background: rgba(244,63,94,0.18); color: #f43f5e; font-weight:600"
    if v >= 0.6:  return "background: rgba(245,158,11,0.18); color: #f59e0b"
    if v >= 0.4:  return "background: rgba(245,158,11,0.10)"
    if v >= 0.2:  return "background: rgba(16,185,129,0.10)"
    if v >= 0:    return "background: rgba(16,185,129,0.18); color: #10b981"
    return "background: rgba(252,136,229,0.15); color: #fc88e5"

COL_FNS = {
    "Sharpe":      lambda v: _c(v, 1.0, 0.5),
    "Sortino":     lambda v: _c(v, 1.0, 0.5),
    "Beta":        col_beta,
    "MaxDrawdown": lambda v: _c(v, -0.10, -0.25, invert=True),
    "VaR":         lambda v: _c(v, -0.015, -0.025, invert=True),
    "CVaR":        lambda v: _c(v, -0.015, -0.025, invert=True),
}

def style_asset_table(df):
    s = df.style
    for col, fn in COL_FNS.items():
        if col in df.columns:
            s = s.map(fn, subset=[col])
    fmt = {c: ("{:.2%}" if c in PCT_METRICS else "{:.3f}") for c in df.columns}
    return s.format(fmt, na_rep="—")

# ── Chart builders ───────────────────────────────────────────────────────────
def _plotly_layout(dark, height=380, ylabel="", xlabel=""):
    bg         = "#0c0c0c" if dark else "#ffffff"
    text_col   = "#f0f0f0" if dark else "#111111"
    grid_col   = "#272727" if dark else "#e8e8e8"
    return dict(
        paper_bgcolor=bg, plot_bgcolor=bg,
        font=dict(family="Inter", color=text_col, size=12),
        height=height, margin=dict(l=0, r=10, t=40, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="left", x=0, bgcolor="rgba(0,0,0,0)",
                    font=dict(size=11)),
        xaxis=dict(title=xlabel, showgrid=True, gridcolor=grid_col,
                   zeroline=False, color=text_col),
        yaxis=dict(title=ylabel, showgrid=True, gridcolor=grid_col,
                   zeroline=True, zerolinecolor=grid_col, color=text_col),
        hovermode="x unified",
    )

_LINE_COLORS = [
    "#fc88e5", "#10b981", "#f59e0b", "#8b8cf8", "#f43f5e",
    "#06b6d4", "#a78bfa", "#fb923c", "#34d399", "#60a5fa",
]

def build_cumulative_chart(price_df, dark=False):
    wide    = price_df.pivot(index="date", columns="ticker", values="close")
    returns = wide.pct_change().dropna(how="all")
    cumret  = (1 + returns).cumprod() - 1

    non_spy = [t for t in returns.columns if t != "SPY"]
    w       = np.ones(len(non_spy)) / len(non_spy)
    port_r  = (returns[non_spy] * w).sum(axis=1)
    cumport = (1 + port_r).cumprod() - 1

    fig = go.Figure()

    # Individual stocks
    for i, ticker in enumerate(non_spy):
        fig.add_trace(go.Scatter(
            x=cumret.index, y=(cumret[ticker] * 100).round(2),
            name=ticker,
            line=dict(color=_LINE_COLORS[i % len(_LINE_COLORS)], width=1.5),
            hovertemplate=f"<b>{ticker}</b>: %{{y:.1f}}%<extra></extra>",
        ))

    # SPY benchmark (dashed grey)
    if "SPY" in cumret.columns:
        spy_col = "#aaaaaa" if dark else "#999999"
        fig.add_trace(go.Scatter(
            x=cumret.index, y=(cumret["SPY"] * 100).round(2),
            name="SPY (Benchmark)",
            line=dict(color=spy_col, width=1.5, dash="dot"),
            hovertemplate="<b>SPY</b>: %{y:.1f}%<extra></extra>",
        ))

    # Equal-weight portfolio (bold)
    port_col = "#f0f0f0" if dark else "#111111"
    fig.add_trace(go.Scatter(
        x=cumport.index, y=(cumport * 100).round(2),
        name="Portfolio (Equal Weight)",
        line=dict(color=port_col, width=2.8),
        hovertemplate="<b>Portfolio</b>: %{y:.1f}%<extra></extra>",
    ))

    layout = _plotly_layout(dark, height=400, ylabel="Cumulative Return (%)")
    layout["hovermode"] = "x unified"
    fig.update_layout(**layout)
    return fig


def build_frontier_chart(price_df, rfr=0.05, dark=False, n=2500):
    wide    = price_df.pivot(index="date", columns="ticker", values="close")
    returns = wide.pct_change().dropna(how="all")

    opt = [t for t in returns.columns if t != "SPY"]
    if len(opt) < 2:
        return None

    r        = returns[opt]
    ann_mean = r.mean() * 252
    ann_cov  = r.cov() * 252
    k        = len(opt)

    rng = np.random.default_rng(42)
    p_vols, p_rets, p_sharpes = [], [], []
    for _ in range(n):
        w      = rng.dirichlet(np.ones(k))
        p_ret  = float((ann_mean * w).sum())
        p_vol  = float(np.sqrt(w @ ann_cov.values @ w))
        p_sharpes.append((p_ret - rfr) / p_vol if p_vol > 0 else 0)
        p_rets.append(p_ret * 100)
        p_vols.append(p_vol * 100)

    # Equal-weight stats
    ew     = np.ones(k) / k
    ew_ret = float((ann_mean * ew).sum()) * 100
    ew_vol = float(np.sqrt(ew @ ann_cov.values @ ew)) * 100

    # Per-stock stats
    s_vols = (np.sqrt(np.diag(ann_cov.values)) * 100).tolist()
    s_rets = (ann_mean.values * 100).tolist()

    text_col = "#f0f0f0" if dark else "#111111"
    port_col = "#f0f0f0" if dark else "#111111"

    fig = go.Figure()

    # Random portfolio cloud coloured by Sharpe
    fig.add_trace(go.Scatter(
        x=p_vols, y=p_rets, mode="markers",
        marker=dict(
            color=p_sharpes, colorscale="RdPu",
            size=3, opacity=0.45,
            colorbar=dict(title=dict(text="Sharpe", side="right"),
                          thickness=12, len=0.55),
        ),
        name="Random Portfolios",
        hovertemplate="Vol: %{x:.1f}%  Return: %{y:.1f}%<extra></extra>",
    ))

    # Individual stocks (pink dots)
    fig.add_trace(go.Scatter(
        x=s_vols, y=s_rets, mode="markers+text",
        marker=dict(color="#fc88e5", size=10,
                    line=dict(color=text_col, width=1)),
        text=opt, textposition="top center",
        textfont=dict(size=10, color=text_col),
        name="Individual Stocks",
        hovertemplate="<b>%{text}</b><br>Vol: %{x:.1f}%  Return: %{y:.1f}%<extra></extra>",
    ))

    # SPY benchmark (grey diamond)
    if "SPY" in returns.columns:
        spy_vol = float(returns["SPY"].std() * np.sqrt(252) * 100)
        spy_ret = float(returns["SPY"].mean() * 252 * 100)
        fig.add_trace(go.Scatter(
            x=[spy_vol], y=[spy_ret], mode="markers+text",
            marker=dict(color="#888888", size=12, symbol="diamond",
                        line=dict(color="#888888", width=1)),
            text=["SPY"], textposition="top center",
            textfont=dict(size=10, color="#888888"),
            name="SPY Benchmark",
            hovertemplate="<b>SPY</b><br>Vol: %{x:.1f}%  Return: %{y:.1f}%<extra></extra>",
        ))

    # Your portfolio (star)
    fig.add_trace(go.Scatter(
        x=[ew_vol], y=[ew_ret], mode="markers+text",
        marker=dict(color=port_col, size=16, symbol="star",
                    line=dict(color="#fc88e5", width=2)),
        text=["Your Portfolio"], textposition="top center",
        textfont=dict(size=11, color=text_col, family="Inter"),
        name="Your Portfolio",
        hovertemplate="<b>Your Portfolio</b><br>Vol: %{x:.1f}%  Return: %{y:.1f}%<extra></extra>",
    ))

    layout = _plotly_layout(dark, height=460,
                            xlabel="Annualized Volatility (%)",
                            ylabel="Annualized Return (%)")
    layout.pop("hovermode")
    layout["hovermode"] = "closest"
    fig.update_layout(**layout)
    return fig


# ── Load universe data ────────────────────────────────────────────────────────
const_df, etfs_df, all_sectors = load_universe()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:

    # Dark mode toggle — top right
    toggle_col, _ = st.columns([1, 0.01])
    with toggle_col:
        new_dark = st.toggle(
            "Dark mode",
            value=st.session_state.dark_mode,
            key="dark_toggle",
        )
    if new_dark != st.session_state.dark_mode:
        st.session_state.dark_mode = new_dark
        st.rerun()

    st.markdown("---")

    # ── Time horizon ──
    st.markdown('<span class="sb-label">Time Horizon</span>', unsafe_allow_html=True)
    time_horizon = st.radio(
        "Time Horizon",
        ["1 Year", "3 Years", "5 Years", "10 Years"],
        index=2,
        label_visibility="collapsed",
    )

    st.markdown("---")

    # ── Sector filter ──
    st.markdown('<span class="sb-label">Filter by Sector</span>', unsafe_allow_html=True)
    selected_sectors = st.multiselect(
        "Filter by Sector",
        options=all_sectors,
        default=[],
        placeholder="All sectors",
        label_visibility="collapsed",
    )

    # ── Stock picker ──
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
        default=[],
        placeholder="Type to search…",
        max_selections=9,
        label_visibility="collapsed",
    )

    # ── ETF picker ──
    st.markdown('<span class="sb-label">ETFs &amp; Indices</span>', unsafe_allow_html=True)
    st.caption("SPY is always included as benchmark.")
    etf_options = etfs_df["label"].tolist() if not etfs_df.empty else []
    selected_etf_labels = st.multiselect(
        "ETFs",
        options=etf_options,
        default=[],
        placeholder="e.g. QQQ, GLD…",
        label_visibility="collapsed",
    )

    st.markdown("---")

    # ── Risk-free rate ──
    st.markdown('<span class="sb-label">Risk-Free Rate</span>', unsafe_allow_html=True)
    rfr_pct = st.slider(
        "Risk-Free Rate",
        min_value=0.0, max_value=10.0, value=5.0,
        step=0.5, format="%.1f%%",
        label_visibility="collapsed",
    )
    rfr = rfr_pct / 100
    st.caption(f"Currently {rfr_pct:.1f}% — this is the 'safe' return (e.g. T-bill) used to measure whether your portfolio rewards you enough for the extra risk taken.")

    st.markdown("---")
    run_btn = st.button("Run Analysis", width="stretch", type="primary")

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
    '<p class="hero-sub">Select stocks and ETFs in the sidebar — search by company name or ticker. '
    "SPY is always included as the S&amp;P 500 benchmark. Click Run Analysis when ready.</p>",
    unsafe_allow_html=True,
)

if not run_btn:
    st.info("Build your portfolio in the sidebar and click **Run Analysis** to begin.", icon="ℹ️")
    st.stop()

# ── Parse selections ──────────────────────────────────────────────────────────
def extract_symbol(label):
    return label.split("  —  ")[0].strip()

chosen = [extract_symbol(l) for l in selected_stock_labels]
chosen += [extract_symbol(l) for l in selected_etf_labels]
chosen = list(dict.fromkeys(chosen))  # dedupe, preserve order

if not chosen:
    st.warning("Select at least one stock or ETF from the sidebar before running analysis.", icon="⚠️")
    st.stop()

if "SPY" not in chosen:
    chosen.insert(0, "SPY")
tickers_list = chosen[:10]

# ── Fetch + compute ───────────────────────────────────────────────────────────
with st.spinner("Fetching data and computing metrics…"):
    try:
        df = helpers.get_price_data(tickers_list, str(start_date), str(end_date))
    except Exception as e:
        st.error(f"Failed to load price data: {e}")
        st.stop()

    actual = df["ticker"].unique().tolist()
    missing = [t for t in tickers_list if t not in actual]
    weights = [1 / len(actual)] * len(actual)

    asset_df  = core.compute_asset_metrics(df, benchmark_ticker="SPY", risk_free_rate=rfr)
    port_dict, corr = core.compute_portfolio_metrics(
        df, weights, benchmark_ticker="SPY", risk_free_rate=rfr
    )

# ── Info bar ──────────────────────────────────────────────────────────────────
chips = " ".join(
    f'<span class="chip {"chip-bench" if t == "SPY" else ""}">{t}</span>'
    for t in actual
)
st.markdown(
    f'<div class="info-bar">'
    f"<b>Portfolio</b> &nbsp; {chips} <br>"
    f"<b>Period</b> &nbsp; {start_date} → {end_date} &nbsp;&nbsp;"
    f"<b>Horizon</b> &nbsp; {time_horizon} &nbsp;&nbsp;"
    f"<b>Risk-free rate</b> &nbsp; {rfr * 100:.1f}% &nbsp;&nbsp;"
    f"<b>Weighting</b> &nbsp; Equal ({100 / len(actual):.0f}% each)"
    f"</div>",
    unsafe_allow_html=True,
)
if missing:
    st.warning(
        f"No data found for: **{', '.join(missing)}**. Only tickers with data are shown.",
        icon="⚠️",
    )

# ── Asset Metrics ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Breakdown</div>', unsafe_allow_html=True)
st.markdown('<div class="section-heading">Asset Metrics</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-desc">'
    "Per-stock risk and return over the selected period. "
    "SPY is the benchmark — Beta, Sharpe, and Sortino are all measured relative to it. "
    "Green = favorable &nbsp;·&nbsp; Amber = neutral &nbsp;·&nbsp; Rose = elevated risk."
    "</div>",
    unsafe_allow_html=True,
)
st.dataframe(style_asset_table(asset_df), width="stretch")

# ── Portfolio Metrics ─────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Combined View</div>', unsafe_allow_html=True)
st.markdown('<div class="section-heading">Portfolio Metrics</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-desc">'
    "Your holdings treated as a single equally-weighted position. "
    "These figures describe how the portfolio behaves as a whole."
    "</div>",
    unsafe_allow_html=True,
)
cols = st.columns(3)
for i, key in enumerate(["Sharpe", "Sortino", "Beta", "MaxDrawdown", "VaR", "CVaR"]):
    with cols[i % 3]:
        st.markdown(metric_card_html(key, port_dict.get(key, np.nan)), unsafe_allow_html=True)

# ── Charts ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Performance</div>', unsafe_allow_html=True)
st.markdown('<div class="section-heading">Cumulative Returns</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-desc">'
    "Growth of $1 invested at the start of the period. The bold line is your equal-weight portfolio, "
    "the dotted line is SPY. Hover over any point to compare values."
    "</div>",
    unsafe_allow_html=True,
)
st.plotly_chart(build_cumulative_chart(df, dark=dark), use_container_width=True)

st.markdown('<div class="section-title">Risk vs. Return</div>', unsafe_allow_html=True)
st.markdown('<div class="section-heading">Efficient Frontier</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-desc">'
    "Each dot in the cloud is one of 2,500 randomly weighted combinations of your stocks, coloured by Sharpe ratio (pink = higher). "
    "Pink dots are your individual stocks. The star is your equal-weight portfolio. "
    "Portfolios toward the <b>upper-left</b> are best — higher return for less risk."
    "</div>",
    unsafe_allow_html=True,
)
frontier_fig = build_frontier_chart(df, rfr=rfr, dark=dark)
if frontier_fig:
    st.plotly_chart(frontier_fig, use_container_width=True)
else:
    st.info("Select at least 2 stocks (excluding SPY) to see the efficient frontier.", icon="ℹ️")

# ── Correlation Matrix ────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Diversification</div>', unsafe_allow_html=True)
st.markdown('<div class="section-heading">Correlation Matrix</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-desc">'
    "How closely each stock moves with the others. "
    "<b style='color:#10b981'>Near 0 or negative</b> = independent or inverse moves (good diversification). "
    "<b style='color:#f43f5e'>Near 1.0</b> = move together (lower diversification)."
    "</div>",
    unsafe_allow_html=True,
)
st.dataframe(
    corr.style.map(corr_cell_css).format("{:.2f}"),
    width="stretch",
)
