"""Rule-based plain-English findings about a portfolio.

Each insight is {"level": good|warn|risk|info, "tag": short label, "text": html}.
Pure function of computed data — no Streamlit imports — so it can be tested
and reasoned about independently of the UI.
"""
import numpy as np
import pandas as pd

_LEVEL_ORDER = {"risk": 0, "warn": 1, "info": 2, "good": 3}


def _fmt_month(ts):
    return ts.strftime("%B %Y")


def generate_insights(
    *,
    corr,
    weights_map,
    sector_map,
    returns_wide,
    port_r,
    bench_r,
    port_metrics,
    div_score,
    opt=None,
    max_items=7,
):
    out = []
    held = [t for t, w in weights_map.items() if w > 0 and t in returns_wide.columns]
    if not held:
        return out
    w_arr = np.array([weights_map[t] for t in held])
    w_arr = w_arr / w_arr.sum()

    # 1 ── Headline vs SPY
    port_total = float((1 + port_r.dropna()).prod() - 1)
    spy_total = float((1 + bench_r.dropna()).prod() - 1)
    port_vol = float(port_r.std() * np.sqrt(252))
    spy_vol = float(bench_r.std() * np.sqrt(252))
    vol_ratio = port_vol / spy_vol if spy_vol > 0 else np.nan
    beat = port_total > spy_total
    if beat and vol_ratio <= 1.05:
        out.append({
            "level": "good", "tag": "vs. Market",
            "text": (f"Your portfolio returned <b>{port_total*100:+.1f}%</b> vs SPY's "
                     f"<b>{spy_total*100:+.1f}%</b> over this period — with "
                     f"{'similar' if vol_ratio > 0.95 else 'less'} volatility "
                     f"({vol_ratio:.2f}× the market's). That's the ideal combination."),
        })
    elif beat:
        out.append({
            "level": "info", "tag": "vs. Market",
            "text": (f"Your portfolio beat SPY (<b>{port_total*100:+.1f}%</b> vs "
                     f"<b>{spy_total*100:+.1f}%</b>), but took <b>{vol_ratio:.2f}×</b> the "
                     f"market's volatility to do it. Higher returns from higher risk — "
                     f"make sure that trade-off is intentional."),
        })
    else:
        out.append({
            "level": "warn", "tag": "vs. Market",
            "text": (f"Your portfolio returned <b>{port_total*100:+.1f}%</b> vs SPY's "
                     f"<b>{spy_total*100:+.1f}%</b> — it underperformed simply holding the "
                     f"index over this period"
                     + (f", while carrying <b>{vol_ratio:.2f}×</b> the volatility." if vol_ratio > 1.05 else ".")),
        })

    # 2 ── Most correlated pair
    if len(held) >= 2:
        sub = corr.loc[held, held]
        best_pair, best_val = None, -np.inf
        for i, a in enumerate(held):
            for b in held[i + 1:]:
                v = float(sub.loc[a, b])
                if v > best_val:
                    best_pair, best_val = (a, b), v
        if best_pair and best_val >= 0.85:
            out.append({
                "level": "risk", "tag": "Correlation",
                "text": (f"<b>{best_pair[0]}</b> and <b>{best_pair[1]}</b> moved almost "
                         f"identically (correlation {best_val:.2f}). They effectively act as "
                         f"one position — you have less diversification than the holding count suggests."),
            })
        elif best_pair and best_val >= 0.70:
            out.append({
                "level": "warn", "tag": "Correlation",
                "text": (f"<b>{best_pair[0]}</b> and <b>{best_pair[1]}</b> are strongly linked "
                         f"(correlation {best_val:.2f}) — expect them to fall together in a downturn."),
            })

    # 3 ── Sector concentration
    buckets = {}
    for t, wt in zip(held, w_arr):
        s = sector_map.get(t)
        s = s if (s and not pd.isna(s)) else "Other / ETF"
        buckets[s] = buckets.get(s, 0.0) + float(wt)
    if buckets:
        top_sector, top_w = max(buckets.items(), key=lambda kv: kv[1])
        if top_w >= 0.50 and len(buckets) > 1:
            out.append({
                "level": "risk", "tag": "Sector",
                "text": (f"<b>{top_sector}</b> makes up <b>{top_w*100:.0f}%</b> of your portfolio. "
                         f"A downturn in one sector would hit most of your money at once."),
            })
        elif top_w >= 0.35 and len(buckets) > 1:
            out.append({
                "level": "warn", "tag": "Sector",
                "text": (f"<b>{top_sector}</b> is your largest sector at <b>{top_w*100:.0f}%</b> "
                         f"of the portfolio — meaningful concentration worth monitoring."),
            })
        elif len(buckets) >= 4:
            out.append({
                "level": "good", "tag": "Sector",
                "text": (f"Your money is spread across <b>{len(buckets)}</b> sectors with no single "
                         f"sector above {top_w*100:.0f}% — a balanced sector footprint."),
            })

    # 4 ── Weight concentration (effective positions)
    n_eff = 1.0 / float((w_arr ** 2).sum())
    if len(held) >= 3 and n_eff < 0.6 * len(held):
        out.append({
            "level": "warn", "tag": "Weights",
            "text": (f"You hold {len(held)} tickers, but your weights concentrate into roughly "
                     f"<b>{n_eff:.1f} effective positions</b> — a few large holdings dominate the risk."),
        })

    # 5 ── Volatility driver
    ann_vol = returns_wide[held].std() * np.sqrt(252)
    driver, driver_w = None, 0.0
    contrib = {t: float(ann_vol[t]) * weights_map[t] for t in held}
    if contrib:
        driver = max(contrib, key=contrib.get)
        driver_w = weights_map[driver]
        if driver_w >= 0.15 and float(ann_vol[driver]) >= 1.25 * float(ann_vol.mean()):
            out.append({
                "level": "info", "tag": "Risk Driver",
                "text": (f"<b>{driver}</b> contributes the most day-to-day swing: "
                         f"{ann_vol[driver]*100:.0f}% annualized volatility at "
                         f"{driver_w*100:.0f}% weight. Trimming it is the fastest way to calm the portfolio."),
            })

    # 6 ── Worst month
    if isinstance(port_r.index, pd.DatetimeIndex) and len(port_r) > 40:
        monthly = port_r.resample("ME").apply(lambda x: float((1 + x).prod() - 1))
        monthly = monthly.dropna()
        if len(monthly) >= 3:
            worst_val = float(monthly.min())
            worst_month = monthly.idxmin()
            if worst_val < -0.03:
                out.append({
                    "level": "info", "tag": "History",
                    "text": (f"Your portfolio's worst month was <b>{_fmt_month(worst_month)}</b> "
                             f"(<b>{worst_val*100:.1f}%</b>). If a repeat of that month would make you "
                             f"sell in a panic, the portfolio may be too aggressive for you."),
                })

    # 7 ── Optimizer gap
    if opt is not None:
        cur_sharpe = port_metrics.get("Sharpe")
        opt_sharpe = opt.get("max_sharpe", {}).get("sharpe")
        if (cur_sharpe is not None and opt_sharpe is not None
                and not pd.isna(cur_sharpe) and opt_sharpe - cur_sharpe >= 0.15):
            out.append({
                "level": "info", "tag": "Optimizer",
                "text": (f"A different mix of <i>the same holdings</i> historically achieved a Sharpe of "
                         f"<b>{opt_sharpe:.2f}</b> vs your <b>{cur_sharpe:.2f}</b>. "
                         f"See the What-If &amp; Optimize tab for the suggested weights."),
            })

    # 8 ── Diversification tip
    if div_score < 40 and len(held) >= 2:
        out.append({
            "level": "info", "tag": "Diversify",
            "text": ("Most of your holdings move together. Assets from other classes — bond ETFs "
                     "(e.g. AGG, BND), gold (GLD), or international funds — tend to move independently "
                     "of US stocks and would raise your diversification score."),
        })

    out.sort(key=lambda d: _LEVEL_ORDER.get(d["level"], 9))
    return out[:max_items]


def insight_html(item):
    level, tag, text = item["level"], item["tag"], item["text"]
    badge_cls = {"good": "bg", "warn": "by", "risk": "br", "info": "bb"}[level]
    return (
        f'<div class="insight insight-{level}">'
        f'<span class="insight-tag {badge_cls}">{tag}</span>{text}'
        f'</div>'
    )
