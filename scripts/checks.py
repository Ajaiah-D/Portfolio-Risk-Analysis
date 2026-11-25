"""Cross-checks on Yahoo's prices that need no second data provider.

Every price in the database comes from Yahoo Finance. These checks test it
against data the pipeline already has:

Twin-fund check
    Funds that track the same index should have near-identical daily total
    returns. On each day, a member whose return is further from the group
    median than the group's tolerance is flagged. A missed or wrong dividend
    adjustment shows as a gap that does not close; a late or stale price
    shows as a gap that reverses the next day.

Adjustment check
    On an ex-dividend or split date, the stored adjusted return must equal
    what Yahoo's own raw closes and dividend record imply:
        raw_close[t] / (raw_close[t-1] - dividend[t]) - 1
    Yahoo's raw close is already split-adjusted, so a split needs no term of
    its own; a stored series that missed it shows a split-sized gap.

Both are warnings. They never stop the refresh or turn a run red; in GitHub
Actions they are also printed as ::warning annotations on the run page.
"""
import os

import numpy as np
import pandas as pd

# ── Twin-fund groups ──────────────────────────────────────────────────────────
# Tolerances are calibrated on the stored history (2020-01-02 onward); see the
# README for the distribution of differences and the flags each candidate
# tolerance raised. Each group's limit on a given day is
#     tolerance + MOVE_SCALE * |group median return|
# because ETF closing prices and fund NAVs drift further apart on big market
# days (March 2020, April 2025). "catches" is the smallest distribution the
# group is meant to catch on a quiet day if a member's adjustment misses it.
#
# In a two-member group the median is the midpoint, so each member sits half
# the gap away: a pair catches a missed distribution of about twice its
# tolerance and cannot tell which member is wrong.
MOVE_SCALE = 0.03

TWIN_GROUPS = {
    "S&P 500": {
        "members": ["SPY", "IVV", "VOO", "FXAIX", "VFIAX"],
        "tolerance": 0.0015,
        "catches": 0.0025,
        "why": "All five hold the S&P 500 index. VOO and VFIAX are two share "
               "classes of the same Vanguard fund. Quarterly dividends are "
               "usually 0.25% to 0.35% of price.",
    },
    "US total market": {
        "members": ["VTI", "VTSAX", "FSKAX", "FZROX"],
        "tolerance": 0.0015,
        "catches": 0.0025,
        "why": "VTI and VTSAX are share classes of one fund (CRSP US Total "
               "Market). FSKAX tracks the Dow Jones US Total Stock Market "
               "index and FZROX Fidelity's US Total Investable Market index: "
               "every listed US stock, cap weighted, so daily returns match "
               "within a few hundredths of a percent.",
    },
    "US aggregate bonds (ETFs)": {
        "members": ["AGG", "BND"],
        "tolerance": 0.0010,
        "catches": 0.0030,
        "why": "AGG tracks the Bloomberg US Aggregate index and BND its "
               "float-adjusted version. Monthly dividends are about 0.33%. "
               "Kept apart from the bond mutual funds: see below.",
    },
    "US aggregate bonds (mutual funds)": {
        "members": ["FXNAX", "VBTLX"],
        "tolerance": 0.0010,
        "catches": 0.0030,
        "why": "FXNAX tracks the Bloomberg US Aggregate index and VBTLX its "
               "float-adjusted version (the same index as BND). Both accrue "
               "income daily and pay it at month end without the NAV "
               "dropping, so Yahoo's adjusted series books a month of income "
               "(about 0.3%) on the last business day. Against the ETFs, "
               "which drop on their ex-date, that is a 0.3% gap every month; "
               "against each other it cancels.",
    },
    "Total international": {
        "members": ["FTIHX", "VTIAX"],
        "tolerance": 0.0015,
        "catches": 0.0040,
        "why": "FTIHX tracks MSCI ACWI ex USA IMI and VTIAX FTSE Global All "
               "Cap ex US: both are every non-US stock, developed and "
               "emerging, large to small. Not the same index, but daily "
               "returns differ by under 0.3% on 99% of days. Both are "
               "mutual funds with fair-valued NAVs, so they are priced at "
               "the same moment. VTIAX's smallest quarterly dividends "
               "(under 0.3%) are below what a pair can catch.",
    },
}
# Not grouped: VEA vs EFA (FTSE Developed includes Canada and small caps,
# MSCI EAFE does not) and VWO vs EEM (FTSE vs MSCI emerging markets, which
# differ on South Korea). Their daily gaps reach 0.4% and 1% in ordinary
# months, so a tolerance that keeps them quiet would miss most dividends.


def twin_flags(closes, groups=None, move_scale=MOVE_SCALE):
    """Return a list of divergences, oldest first.

    closes: DataFrame of adjusted closes, one column per ticker, indexed by
    date. Missing values are allowed; a return is only computed between two
    consecutive stored days, and a day needs at least two members with a
    return to be compared.

    Each flag is a dict: group, date (ISO string), ticker, ret, median,
    deviation (ret - median), limit, reverses (True when the next day's gap
    undoes it, False when it does not, None on the latest day),
    undoes_previous (True when this day closes the previous day's gap: the
    catch-up day of a late price), and members ({ticker: return} for that
    day, for the report line).

    A flag with reverses False and undoes_previous False is a gap that
    stays open: the signature of a missed distribution or bad adjustment.
    """
    groups = TWIN_GROUPS if groups is None else groups
    closes = closes.sort_index()
    flags = []
    for name, spec in groups.items():
        members = [m for m in spec["members"] if m in closes.columns]
        if len(members) < 2:
            continue
        rets = closes[members].pct_change(fill_method=None)
        enough = rets.notna().sum(axis=1) >= 2
        rets = rets[enough]
        if rets.empty:
            continue
        median = rets.median(axis=1)
        dev = rets.sub(median, axis=0)
        limit = spec["tolerance"] + move_scale * median.abs()
        over = dev.abs().gt(limit, axis=0)
        dates = list(rets.index)

        def closes_gap(i, j, col):
            """True if days i and j (adjacent) together leave no gap."""
            d_i, d_j = dev.iat[i, col], dev.iat[j, col]
            if np.isnan(d_i) or np.isnan(d_j):
                return False
            return bool(abs(d_i + d_j) <= max(limit.iat[i], limit.iat[j]))

        for i, day in enumerate(dates):
            for ticker in [m for m in members if over.at[day, m]]:
                col = members.index(ticker)
                has_next = i + 1 < len(dates) and not np.isnan(dev.iat[i + 1, col])
                reverses = closes_gap(i, i + 1, col) if has_next else None
                undoes_previous = (i > 0 and bool(over.iat[i - 1, col])
                                   and closes_gap(i - 1, i, col))
                flags.append({
                    "group": name,
                    "date": pd.Timestamp(day).date().isoformat(),
                    "ticker": ticker,
                    "ret": float(rets.at[day, ticker]),
                    "median": float(median.at[day]),
                    "deviation": float(dev.at[day, ticker]),
                    "limit": float(limit.at[day]),
                    "reverses": reverses,
                    "undoes_previous": undoes_previous,
                    "members": {m: float(rets.at[day, m]) for m in members
                                if not np.isnan(rets.at[day, m])},
                })
    flags.sort(key=lambda f: (f["date"], f["group"], f["ticker"]))
    return flags


# ── Adjustment check ──────────────────────────────────────────────────────────
# Calibrated on 1,686 dividend and split events (a sample of S&P 500 stocks
# plus the grouped funds and ETFs, 2020 onward): Yahoo's adjusted returns
# matched the formula above to within 0.0001%. The tolerance is 200 times
# that, and below any dividend worth worrying about.
ADJUSTMENT_TOLERANCE = 0.0002

RAW_COLUMNS = ("close_raw", "dividend", "split")


def adjustment_mismatches(frame, tolerance=ADJUSTMENT_TOLERANCE):
    """Return [{date, stored, implied, dividend, split}] for ex-dividend and
    split dates where the stored adjusted return disagrees with the raw
    closes and the dividend record.

    frame: one ticker's rows in date order with `close` (adjusted, as
    stored), `close_raw`, `dividend` (cash dividend plus capital gains) and
    `split` (ratio, 0 when none). Frames without the raw columns (older
    callers, test fakes) are skipped.
    """
    if frame.empty or any(c not in frame.columns for c in RAW_COLUMNS):
        return []
    df = frame.sort_values("date").reset_index(drop=True)
    close = pd.to_numeric(df["close"], errors="coerce").to_numpy(dtype=float)
    raw = pd.to_numeric(df["close_raw"], errors="coerce").to_numpy(dtype=float)
    div = pd.to_numeric(df["dividend"], errors="coerce").fillna(0).to_numpy(dtype=float)
    split = pd.to_numeric(df["split"], errors="coerce").fillna(0).to_numpy(dtype=float)

    found = []
    for i in range(1, len(df)):
        has_split = split[i] > 0 and split[i] != 1
        if div[i] <= 0 and not has_split:
            continue
        base = raw[i - 1] - div[i]
        if not (close[i - 1] > 0 and base > 0 and raw[i] > 0):
            continue
        stored = close[i] / close[i - 1] - 1
        implied = raw[i] / base - 1
        if abs(stored - implied) > tolerance:
            found.append({
                "date": str(df["date"].iloc[i]),
                "stored": float(stored),
                "implied": float(implied),
                "dividend": float(div[i]),
                "split": float(split[i]),
            })
    return found


# ── Reporting ─────────────────────────────────────────────────────────────────
def annotate_warning(title, message):
    """Print a GitHub Actions warning annotation (shown on the run page
    without failing it). Does nothing outside Actions."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::warning title={title}::{message}", flush=True)
