"""Metric interpretation: badge classes, plain-English descriptions,
reference ranges, metric card HTML, and dataframe stylers."""
import pandas as pd

PCT_METRICS = {"MaxDrawdown", "VaR", "CVaR"}
PCT_DISPLAY = {"MaxDrawdown", "VaR", "CVaR"}
INT_DISPLAY = {"DivScore"}


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

def interpret_div_score(v):
    if pd.isna(v): return "bb", "N/A", ""
    if v >= 65: return "bg", "Well Diversified", f"Score {v:.0f}/100 — holdings move independently, reducing overall risk."
    if v >= 45: return "by", "Moderate", f"Score {v:.0f}/100 — some overlap in how holdings move. Uncorrelated assets would help."
    if v >= 25: return "by", "Concentrated", f"Score {v:.0f}/100 — many holdings move together. A market drop likely hits all at once."
    return "br", "Highly Concentrated", f"Score {v:.0f}/100 — holdings are tightly correlated. Little diversification benefit."


INTERPRETERS = {
    "Sharpe": interpret_sharpe, "Sortino": interpret_sortino,
    "Beta": interpret_beta, "MaxDrawdown": interpret_drawdown,
    "VaR": interpret_var, "CVaR": interpret_cvar,
    "DivScore": interpret_div_score,
}
METRIC_DISPLAY = {
    "Sharpe": "Sharpe Ratio", "Sortino": "Sortino Ratio", "Beta": "Beta",
    "MaxDrawdown": "Max Drawdown", "VaR": "Value at Risk (5%)", "CVaR": "CVaR / Exp. Shortfall",
    "DivScore": "Diversification Score",
}

# Each entry: list of (badge_class, range_label, rating_label)
METRIC_RANGES = {
    "Sharpe": [
        ("br", "< 0",    "Negative"),
        ("by", "0–0.5",  "Weak"),
        ("by", "0.5–1",  "Acceptable"),
        ("bg", "> 1",    "Strong"),
        ("bg", "> 2",    "Exceptional"),
    ],
    "Sortino": [
        ("br", "< 0",    "Poor"),
        ("by", "0–0.5",  "Limited"),
        ("by", "0.5–1",  "Moderate"),
        ("bg", "> 1",    "Good"),
        ("bg", "> 2",    "Excellent"),
    ],
    "Beta": [
        ("bp", "< 0",      "Inverse"),
        ("bg", "0–0.5",    "Defensive"),
        ("by", "0.8–1.2",  "Market-like"),
        ("by", "1.2–1.5",  "Aggressive"),
        ("br", "> 1.5",    "Very Aggressive"),
    ],
    "MaxDrawdown": [
        ("bg", "> −5%",    "Minimal"),
        ("bg", "−5–15%",   "Low"),
        ("by", "−15–25%",  "Moderate"),
        ("by", "−25–40%",  "Severe"),
        ("br", "< −40%",   "Extreme"),
    ],
    "VaR": [
        ("bg", "< 1.5%",   "Low"),
        ("by", "1.5–2.5%", "Moderate"),
        ("by", "2.5–3.5%", "Elevated"),
        ("br", "> 3.5%",   "High"),
    ],
    "CVaR": [
        ("bg", "< 2%",     "Low"),
        ("by", "2–3%",     "Moderate"),
        ("by", "3–4.5%",   "Elevated"),
        ("br", "> 4.5%",   "Severe"),
    ],
    "DivScore": [
        ("br", "0–25",   "Highly Concentrated"),
        ("by", "25–45",  "Concentrated"),
        ("by", "45–65",  "Moderate"),
        ("bg", "65–100", "Well Diversified"),
    ],
}


def _ranges_html(key):
    tags = METRIC_RANGES.get(key, [])
    if not tags:
        return ""
    items = "".join(
        f'<span class="rtag rtag-{cls}"><b>{rng}</b>&nbsp;{lbl}</span>'
        for cls, rng, lbl in tags
    )
    return f'<div class="mcard-ranges">{items}</div>'


def metric_card_html(key, value):
    label = METRIC_DISPLAY.get(key, key)
    cls, badge, desc = INTERPRETERS[key](value)
    if pd.isna(value):
        val_str = "—"
    elif key in PCT_DISPLAY:
        val_str = f"{value * 100:.2f}%"
    elif key in INT_DISPLAY:
        val_str = f"{value:.0f} / 100"
    else:
        val_str = f"{value:.3f}"
    return (
        f'<div class="mcard">'
        f'  <div class="mcard-label">{label}</div>'
        f'  <div class="mcard-val">{val_str}</div>'
        f'  <span class="mcard-badge {cls}">{badge}</span>'
        f'  <hr class="mcard-rule"/>'
        f'  <div class="mcard-desc">{desc}</div>'
        f'  {_ranges_html(key)}'
        f'</div>'
    )


# ── Asset table styling ───────────────────────────────────────────────────────
def _c(v, good_thresh, warn_thresh):
    if pd.isna(v): return "color: #8b8cf8"
    if v >= good_thresh: return "color: #10b981; font-weight: 600"
    if v >= warn_thresh: return "color: #f59e0b"
    return "color: #f43f5e"

def col_beta(v):
    if pd.isna(v): return "color: #8b8cf8"
    if 0.8 <= v <= 1.2: return "color: #f59e0b"
    if v < 0.8:         return "color: #10b981; font-weight: 600"
    if v <= 1.5:        return "color: #f59e0b"
    return "color: #f43f5e"

def col_drawdown(v):
    # v is negative; closer to 0 is better
    if pd.isna(v): return "color: #8b8cf8"
    if v > -0.10:  return "color: #10b981; font-weight: 600"
    if v > -0.25:  return "color: #f59e0b"
    return "color: #f43f5e"

def col_var(v):
    # v is negative; closer to 0 is better
    if pd.isna(v): return "color: #8b8cf8"
    if v > -0.015: return "color: #10b981; font-weight: 600"
    if v > -0.025: return "color: #f59e0b"
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
    "MaxDrawdown": col_drawdown,
    "VaR":         col_var,
    "CVaR":        col_var,
}


def style_asset_table(df):
    s = df.style
    for col, fn in COL_FNS.items():
        if col in df.columns:
            s = s.map(fn, subset=[col])
    fmt = {c: ("{:.2%}" if c in PCT_METRICS else "{:.3f}") for c in df.columns}
    return s.format(fmt, na_rep="—")
