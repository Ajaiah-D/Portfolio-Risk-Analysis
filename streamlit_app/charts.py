"""Plotly chart builders. All builders are pure functions of data + theme so
they can be exercised without a running Streamlit server."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go


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

_SECTOR_COLORS = [
    "#fc88e5", "#10b981", "#f59e0b", "#8b8cf8", "#f43f5e",
    "#06b6d4", "#a78bfa", "#fb923c", "#34d399", "#60a5fa", "#e879f9",
]


def build_cumulative_chart(price_df, weights_map, dark=False):
    """Cumulative returns: held tickers (thin), weighted portfolio (bold),
    SPY benchmark (dashed)."""
    wide    = price_df.pivot(index="date", columns="ticker", values="close")
    returns = wide.ffill().pct_change(fill_method=None).dropna(how="all")
    cumret  = (1 + returns).cumprod() - 1

    held = [t for t, w in weights_map.items() if w > 0 and t in returns.columns]
    port_r  = (returns[held] * np.array([weights_map[t] for t in held])).sum(axis=1)
    cumport = (1 + port_r).cumprod() - 1

    fig = go.Figure()

    for i, ticker in enumerate(held):
        fig.add_trace(go.Scatter(
            x=cumret.index, y=(cumret[ticker] * 100).round(2),
            name=ticker,
            line=dict(color=_LINE_COLORS[i % len(_LINE_COLORS)], width=1.5),
            hovertemplate=f"<b>{ticker}</b>: %{{y:.1f}}%<extra></extra>",
        ))

    if "SPY" in cumret.columns:
        spy_col = "#aaaaaa" if dark else "#999999"
        fig.add_trace(go.Scatter(
            x=cumret.index, y=(cumret["SPY"] * 100).round(2),
            name="SPY (Benchmark)",
            line=dict(color=spy_col, width=1.5, dash="dot"),
            hovertemplate="<b>SPY</b>: %{y:.1f}%<extra></extra>",
        ))

    port_col = "#f0f0f0" if dark else "#111111"
    fig.add_trace(go.Scatter(
        x=cumport.index, y=(cumport * 100).round(2),
        name="Your Portfolio",
        line=dict(color=port_col, width=2.8),
        hovertemplate="<b>Portfolio</b>: %{y:.1f}%<extra></extra>",
    ))

    layout = _plotly_layout(dark, height=400, ylabel="Cumulative Return (%)")
    fig.update_layout(**layout)
    return fig


def build_frontier_chart(price_df, weights_map, rfr=0.05, dark=False, n=2500,
                         opt_points=None):
    """Random-portfolio cloud + individual holdings + SPY + your portfolio.
    opt_points: optional {label: (vol_pct, ret_pct)} markers (optimiser output).
    """
    wide    = price_df.pivot(index="date", columns="ticker", values="close")
    returns = wide.ffill().pct_change(fill_method=None).dropna(how="all")

    held = [t for t, w in weights_map.items() if w > 0 and t in returns.columns]
    if len(held) < 2:
        return None

    r        = returns[held]
    ann_mean = r.mean() * 252
    ann_cov  = r.cov() * 252
    k        = len(held)

    rng = np.random.default_rng(42)
    W = rng.dirichlet(np.ones(k), size=n)
    p_rets = W @ ann_mean.values
    p_vols = np.sqrt(np.einsum("ij,jk,ik->i", W, ann_cov.values, W))
    with np.errstate(divide="ignore", invalid="ignore"):
        p_sharpes = np.where(p_vols > 0, (p_rets - rfr) / p_vols, 0.0)
    p_rets, p_vols = p_rets * 100, p_vols * 100

    # Your portfolio stats
    yw = np.array([weights_map[t] for t in held])
    yw = yw / yw.sum()
    y_ret = float(yw @ ann_mean.values) * 100
    y_vol = float(np.sqrt(yw @ ann_cov.values @ yw)) * 100

    s_vols = (np.sqrt(np.diag(ann_cov.values)) * 100).tolist()
    s_rets = (ann_mean.values * 100).tolist()

    text_col = "#f0f0f0" if dark else "#111111"
    port_col = "#f0f0f0" if dark else "#111111"

    fig = go.Figure()
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
    fig.add_trace(go.Scatter(
        x=s_vols, y=s_rets, mode="markers+text",
        marker=dict(color="#fc88e5", size=10,
                    line=dict(color=text_col, width=1)),
        text=held, textposition="top center",
        textfont=dict(size=10, color=text_col),
        name="Individual Holdings",
        hovertemplate="<b>%{text}</b><br>Vol: %{x:.1f}%  Return: %{y:.1f}%<extra></extra>",
    ))

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

    if opt_points:
        symbols = {"Max Sharpe": ("#10b981", "star-triangle-up"),
                   "Min Volatility": ("#8b8cf8", "star-square")}
        for label, (v, rt) in opt_points.items():
            color, sym = symbols.get(label, ("#f59e0b", "circle"))
            fig.add_trace(go.Scatter(
                x=[v], y=[rt], mode="markers+text",
                marker=dict(color=color, size=14, symbol=sym,
                            line=dict(color=text_col, width=1)),
                text=[label], textposition="bottom center",
                textfont=dict(size=10, color=color),
                name=label,
                hovertemplate=f"<b>{label}</b><br>Vol: %{{x:.1f}}%  Return: %{{y:.1f}}%<extra></extra>",
            ))

    fig.add_trace(go.Scatter(
        x=[y_vol], y=[y_ret], mode="markers+text",
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
    layout["hovermode"] = "closest"
    fig.update_layout(**layout)
    return fig


def build_sector_chart(price_df, weights_map, dark=False):
    sector_map = (
        price_df.drop_duplicates("ticker")
        .set_index("ticker")["sector"]
        .to_dict()
    )
    bucket = {}
    for ticker, w in weights_map.items():
        if w <= 0:
            continue
        s = sector_map.get(ticker) or "Other / ETF"
        if pd.isna(s):
            s = "Other / ETF"
        bucket[s] = bucket.get(s, 0) + w

    labels = list(bucket.keys())
    values = [bucket[l] * 100 for l in labels]
    text_col = "#f0f0f0" if dark else "#111111"
    bg       = "#0c0c0c" if dark else "#ffffff"

    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.5,
        textinfo="label+percent",
        textfont=dict(family="Inter", size=11, color=text_col),
        marker=dict(colors=_SECTOR_COLORS[:len(labels)]),
        hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor=bg,
        font=dict(family="Inter", color=text_col),
        height=320, margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(
            orientation="v", yanchor="middle", y=0.5,
            xanchor="left", x=1.02,
            font=dict(size=11, color=text_col),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    return fig


def build_underwater_chart(port_r, dark=False):
    """Drawdown-from-peak over time — shows when losses happened and how long
    recovery took, not just the single worst number."""
    cum = (1 + port_r).cumprod()
    dd  = (cum / cum.cummax() - 1) * 100
    trough_idx = dd.idxmin()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dd.index, y=dd.round(2),
        fill="tozeroy",
        fillcolor="rgba(244,63,94,0.18)",
        line=dict(color="#f43f5e", width=1.6),
        name="Drawdown",
        hovertemplate="%{y:.1f}% below peak<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[trough_idx], y=[round(float(dd.min()), 2)],
        mode="markers+text",
        marker=dict(color="#f43f5e", size=9),
        text=[f"{dd.min():.1f}%"], textposition="bottom center",
        textfont=dict(size=11, color="#f43f5e"),
        name="Max Drawdown",
        hovertemplate="<b>Worst point</b>: %{y:.1f}%<extra></extra>",
    ))
    layout = _plotly_layout(dark, height=320, ylabel="Drawdown from Peak (%)")
    fig.update_layout(**layout)
    return fig


def _rolling_window(n_obs):
    """~3 trading months when there's enough history, shorter for 1Y views."""
    return 63 if n_obs >= 250 else max(21, n_obs // 6)


def build_rolling_vol_chart(port_r, bench_r, dark=False):
    w = _rolling_window(len(port_r))
    pv = port_r.rolling(w).std() * np.sqrt(252) * 100
    bv = bench_r.rolling(w).std() * np.sqrt(252) * 100

    spy_col = "#aaaaaa" if dark else "#999999"
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pv.index, y=pv.round(2), name="Portfolio",
        line=dict(color="#fc88e5", width=2),
        hovertemplate="Portfolio: %{y:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=bv.index, y=bv.round(2), name="SPY",
        line=dict(color=spy_col, width=1.5, dash="dot"),
        hovertemplate="SPY: %{y:.1f}%<extra></extra>",
    ))
    layout = _plotly_layout(dark, height=320,
                            ylabel=f"Rolling {w}-Day Volatility (Annualized %)")
    fig.update_layout(**layout)
    return fig


def build_rolling_beta_chart(port_r, bench_r, dark=False):
    w = _rolling_window(len(port_r))
    aligned = pd.concat([port_r, bench_r], axis=1).dropna()
    p, b = aligned.iloc[:, 0], aligned.iloc[:, 1]
    rolling_beta = p.rolling(w).cov(b) / b.rolling(w).var()

    grid_col = "#272727" if dark else "#e8e8e8"
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=rolling_beta.index, y=rolling_beta.round(3), name="Rolling Beta",
        line=dict(color="#8b8cf8", width=2),
        hovertemplate="Beta: %{y:.2f}<extra></extra>",
    ))
    fig.add_hline(
        y=1.0, line=dict(color=grid_col, width=1.2, dash="dash"),
        annotation_text="  Market (β = 1)",
        annotation_font=dict(size=10, color="#888888"),
        annotation_position="right",
    )
    layout = _plotly_layout(dark, height=320,
                            ylabel=f"Rolling {w}-Day Beta vs SPY")
    fig.update_layout(**layout)
    return fig


def build_monte_carlo(port_r_series, portfolio_value, target_value, years,
                      dark=False, n_sim=1000):
    mu    = float(port_r_series.mean())
    sigma = float(port_r_series.std())
    n_days = max(int(years * 252), 1)

    rng   = np.random.default_rng(0)
    daily = rng.normal(mu, sigma, size=(n_sim, n_days))
    cum   = np.cumprod(1 + daily, axis=1) * portfolio_value

    x    = np.linspace(years / n_days, years, n_days)
    p10  = np.percentile(cum, 10,  axis=0)
    p25  = np.percentile(cum, 25,  axis=0)
    p50  = np.percentile(cum, 50,  axis=0)
    p75  = np.percentile(cum, 75,  axis=0)
    p90  = np.percentile(cum, 90,  axis=0)

    final       = cum[:, -1]
    prob        = float((final >= target_value).mean())
    median_out  = float(np.median(final))
    p10_out     = float(np.percentile(final, 10))
    p90_out     = float(np.percentile(final, 90))

    bg       = "#0c0c0c" if dark else "#ffffff"
    text_col = "#f0f0f0" if dark else "#111111"
    grid_col = "#272727" if dark else "#e8e8e8"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=np.concatenate([x, x[::-1]]),
        y=np.concatenate([p90, p10[::-1]]),
        fill="toself", fillcolor="rgba(139,140,248,0.10)",
        line=dict(color="rgba(0,0,0,0)"),
        name="10th–90th %ile", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=np.concatenate([x, x[::-1]]),
        y=np.concatenate([p75, p25[::-1]]),
        fill="toself", fillcolor="rgba(139,140,248,0.22)",
        line=dict(color="rgba(0,0,0,0)"),
        name="25th–75th %ile", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=p50,
        name="Median outcome",
        line=dict(color="#8b8cf8", width=2.5),
        hovertemplate="Year %{x:.1f}: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_hline(
        y=target_value,
        line=dict(color="#fc88e5", width=1.5, dash="dot"),
        annotation_text=f"  Target ${target_value:,.0f}",
        annotation_font=dict(color="#fc88e5", size=11),
        annotation_position="right",
    )
    fig.add_hline(
        y=portfolio_value,
        line=dict(color=grid_col, width=1, dash="dot"),
        annotation_text=f"  Start ${portfolio_value:,.0f}",
        annotation_font=dict(color=text_col, size=10),
        annotation_position="right",
    )
    fig.update_layout(
        paper_bgcolor=bg, plot_bgcolor=bg,
        font=dict(family="Inter", color=text_col, size=12),
        height=400, margin=dict(l=0, r=120, t=20, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        xaxis=dict(title="Years", showgrid=True, gridcolor=grid_col, color=text_col),
        yaxis=dict(title="Portfolio Value", showgrid=True, gridcolor=grid_col,
                   color=text_col, tickprefix="$", tickformat=",.0f"),
        hovermode="x unified",
    )
    return fig, prob, median_out, p10_out, p90_out
