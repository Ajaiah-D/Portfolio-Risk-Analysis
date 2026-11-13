"""CSS injection for the Streamlit app.

Light/dark theming is native: .streamlit/config.toml defines [theme.light]
and [theme.dark], and Streamlit paints its own widgets in whichever mode is
active. This file deliberately never restyles Streamlit widgets - doing that
means targeting Streamlit's private DOM, which changes between releases and
is what previously broke dark mode.

What's left is styling for the app's own HTML (cards, chips, section
headers). Those colors are derived from `currentColor`, the text color the
active theme sets, so they follow light/dark automatically with no Python
rerun and no knowledge of which theme is on.
"""
import streamlit as st

_CSS = """
<style>
:root {
    /* Neutral tokens: mixes of the inherited theme text color, so the same
       rule reads correctly on a white or near-black background. */
    --muted:  color-mix(in srgb, currentColor 62%, transparent);
    --tint:   color-mix(in srgb, currentColor 4%, transparent);
    --tint2:  color-mix(in srgb, currentColor 8%, transparent);
    --line:   color-mix(in srgb, currentColor 14%, transparent);
    --shadow: rgba(0,0,0,0.08);
    /* Near-square corners everywhere; matches baseRadius in config.toml. */
    --radius: 2px;

    /* Wine accent for the app's own chrome (labels, borders, chips, badges).
       It is never a data colour: charts use indigo (see charts.py). Per-mode
       values match primaryColor in .streamlit/config.toml; light-dark()
       resolves against the color-scheme Streamlit sets for the active theme,
       and browsers without it keep the plain values set here. */
    --accent:     #db2777;
    --accent-dim: rgba(219,39,119,0.12);
    --good:       #10b981;
    --good-dim:   rgba(16,185,129,0.14);
    --warn:       #f59e0b;
    --warn-dim:   rgba(245,158,11,0.14);
    --risk:       #f43f5e;
    --risk-dim:   rgba(244,63,94,0.14);
    --neutral:    #8b8cf8;
    --neutral-dim:rgba(139,140,248,0.14);
    /* Gains and losses (Total Return / Volatility vs SPY): darker green and
       red than the status colours, so the text keeps its contrast. */
    --up:         #16a34a;
    --down:       #dc2626;
    /* Civic layout: a strong rule for tiles and a softer ink for labels. */
    --rule-strong: color-mix(in srgb, currentColor 75%, transparent);
    --ink2:        color-mix(in srgb, currentColor 78%, transparent);
}
@supports (color: light-dark(#000, #fff)) {
    :root {
        --accent:     light-dark(#9d174d, #e0789f);
        --accent-dim: light-dark(rgba(157,23,77,0.10), rgba(224,120,159,0.16));
        --up:         light-dark(#15803d, #22c55e);
        --down:       light-dark(#b91c1c, #f87171);
    }
}

/* ── Page width ──
   layout="wide" still caps content with a max-width and wide side padding,
   which left large empty margins beside the sidebar. Let content use the
   available width, with a cap only for very wide monitors. */
.block-container {
    padding: 2rem 2.5rem 3rem 2.5rem;
    max-width: 1800px;
}
@media (max-width: 640px) {
    .block-container { padding-left: 1rem; padding-right: 1rem; }
}

/* Streamlit's default drag-resized sidebar width is narrower than the
   Weighting and Time Horizon segmented controls need, so they wrap onto a
   second row. min-width sets a floor on desktop without disabling the drag
   handle. Scoped to viewports wide enough to have a docked sidebar (on
   phones Streamlit renders it as a full-width overlay drawer). */
@media (min-width: 640px) {
    [data-testid="stSidebar"] { min-width: 380px !important; }
}

/* ── Typography ── */
.hero-title {
    font-size: 2.3rem; font-weight: 700;
    letter-spacing: -0.8px; margin: 0 0 0.35rem 0; padding: 0;
}
.hero-title span { color: var(--accent); }
.hero-sub {
    font-size: 0.95rem; color: var(--muted);
    margin: 0 0 1.6rem 0; line-height: 1.65; max-width: 52rem;
}

/* ── Section headers ── */
/* A thin rule opens each section; the kicker is quiet, the heading carries
   the weight. */
.section-title {
    font-size: 0.75rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--muted);
    border-top: 1px solid var(--line);
    padding-top: 1.1rem;
    margin: 2.2rem 0 0.3rem 0;
}
.section-heading {
    font-size: 1.25rem; font-weight: 700;
    margin: 0 0 0.35rem 0;
}
.section-desc {
    font-size: 0.82rem; color: var(--muted);
    margin: 0 0 1.1rem 0; line-height: 1.55;
}
hr.section-rule {
    border: none; border-top: 1px solid var(--line); margin: 0.5rem 0 1.2rem 0;
}

/* ── Info bar ── */
.info-bar {
    background: var(--tint);
    border-left: 4px solid var(--accent);
    border-radius: var(--radius);
    padding: 1rem 1.25rem;
    margin-bottom: 1.6rem;
    font-size: 0.84rem; line-height: 1.8;
}
.info-bar b { font-weight: 600; }

/* ── Insight cards ── */
.insight {
    background: var(--tint);
    border-radius: var(--radius);
    padding: 0.9rem 1.15rem;
    margin-bottom: 0.5rem;
    font-size: 0.86rem; line-height: 1.6;
}
.insight b { font-weight: 600; }
.insight-good { border-left: 4px solid var(--good); }
.insight-warn { border-left: 4px solid var(--warn); }
.insight-risk { border-left: 4px solid var(--risk); }
.insight-info { border-left: 4px solid var(--neutral); }
.insight-tag {
    display: inline-block; padding: 0.1rem 0.5rem; margin-right: 0.5rem;
    border-radius: var(--radius); font-size: 0.63rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.06em;
}

/* ── Scorecard row ── */
/* KPI tiles: a flat surface with a rule along the top instead of a boxed,
   shadowed card. The headline row gets the wine rule, metric cards a
   neutral one. */
.scard, .mcard {
    background: var(--tint);
    border-radius: 0;
    margin-bottom: 0.75rem;
}
.scard { padding: 0.9rem 1.1rem 1rem 1.1rem; border-top: 3px solid var(--accent); }
.mcard { padding: 1.1rem 1.25rem 1.2rem 1.25rem; border-top: 3px solid var(--rule-strong); }
.scard-label {
    font-size: 0.85rem; font-weight: 700;
    color: var(--ink2); margin-bottom: 0.2rem;
}
.scard-val {
    font-size: 1.85rem; font-weight: 700;
    line-height: 1.2;
}
.scard-sub {
    font-size: 0.74rem; color: var(--muted); margin-top: 0.2rem;
}
.scard-sub b { font-weight: 600; }
/* Optimizer scorecards reuse badge classes (.bg/.by/.bb) for their value color;
   keep the color but drop the badge's tinted background. */
.scard-val.bg, .scard-val.by, .scard-val.bb { background: none; }
.pos { color: var(--up) !important; }
.neg { color: var(--down) !important; }

/* ── In-brief strip ──
   A short written summary at the top of the Overview, like a statistics
   bulletin. Each line has a square marker: green/red for a gain or loss,
   the status colours for better/worse than SPY, grey for context. */
.brief {
    background: var(--tint);
    border-left: 4px solid var(--accent);
    padding: 1rem 1.25rem 0.85rem 1.25rem;
    margin: 0.3rem 0 0.4rem 0;
}
.brief-head {
    display: flex; flex-wrap: wrap; align-items: baseline;
    gap: 0.6rem; margin: 0 0 0.45rem 0;
}
.brief-title { font-size: 1.05rem; font-weight: 700; }
.brief-vs { font-size: 0.85rem; color: var(--muted); }
.brief-item {
    display: flex; align-items: flex-start; gap: 0.6rem;
    font-size: 0.95rem; line-height: 1.55; margin: 0.35rem 0;
}
.brief-item strong { font-weight: 700; }
.brief-dot { flex: none; width: 10px; height: 10px; margin-top: 0.45rem; }
.brief-dot-up      { background: var(--up); }
.brief-dot-down    { background: var(--down); }
.brief-dot-good    { background: var(--good); }
.brief-dot-bad     { background: var(--risk); }
.brief-dot-warn    { background: var(--warn); }
.brief-dot-neutral { background: var(--muted); }

/* ── Chips ── */
.chip {
    display: inline-block;
    background: var(--tint2); border: 1px solid var(--line);
    border-radius: var(--radius); padding: 0.12rem 0.5rem;
    font-size: 0.75rem; font-weight: 600; margin: 0.1rem;
}
.chip-bench {
    background: var(--accent-dim); border-color: var(--accent); color: var(--accent);
}

/* ── Metric cards ── */
.mcard-label {
    font-size: 0.85rem; font-weight: 700;
    color: var(--ink2); margin-bottom: 0.3rem;
}
.mcard-val {
    font-size: 1.75rem; font-weight: 700;
    line-height: 1; margin-bottom: 0.4rem;
}
.mcard-badge {
    display: inline-block; padding: 0.15rem 0.55rem;
    border-radius: var(--radius); font-size: 0.67rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.5rem;
}
.bg { background: var(--good-dim);    color: var(--good);    }
.by { background: var(--warn-dim);    color: var(--warn);    }
.br { background: var(--risk-dim);    color: var(--risk);    }
.bb { background: var(--neutral-dim); color: var(--neutral); }
.bp { background: var(--accent-dim);    color: var(--accent);    }

.mcard-rule { border: none; border-top: 1px solid var(--line); margin: 0.5rem 0; }
.mcard-desc { font-size: 0.79rem; color: var(--muted); line-height: 1.45; }
.mcard-ranges {
    display: flex; flex-wrap: wrap; gap: 0.28rem;
    margin-top: 0.5rem; padding-top: 0.45rem;
    border-top: 1px dashed var(--line);
}
.rtag {
    font-size: 0.63rem; padding: 0.13rem 0.42rem;
    border-radius: var(--radius); white-space: nowrap; line-height: 1.5;
}
.rtag-bg { background: var(--good-dim);    color: var(--good);    }
.rtag-by { background: var(--warn-dim);    color: var(--warn);    }
.rtag-br { background: var(--risk-dim);    color: var(--risk);    }
.rtag-bb { background: var(--neutral-dim); color: var(--neutral); }
.rtag-bp { background: var(--accent-dim);    color: var(--accent);    }

/* ── Onboarding steps ── */
.step-card {
    background: var(--tint);
    border-top: 3px solid var(--accent);
    padding: 1.2rem 1.35rem;
    min-height: 7.5rem;
}
.step-num {
    display: inline-block; width: 1.7rem; height: 1.7rem;
    border-radius: var(--radius);
    background: var(--accent-dim);
    color: var(--accent);
    font-weight: 700; font-size: 0.8rem; text-align: center; line-height: 1.7rem;
    margin-bottom: 0.55rem;
}
.step-title { font-size: 0.92rem; font-weight: 600; margin-bottom: 0.25rem; }
.step-desc { font-size: 0.8rem; color: var(--muted); line-height: 1.5; }

/* ── Glossary cards ── */
.gcard {
    background: var(--tint); border: 1px solid var(--line);
    border-radius: var(--radius); padding: 1.35rem 1.5rem;
    box-shadow: 0 1px 4px var(--shadow); margin-bottom: 0.75rem;
}
.gcard-term { font-size: 1rem; font-weight: 700; margin-bottom: 0.3rem; }
.gcard-tag {
    display: inline-block; font-size: 0.65rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.08em;
    padding: 0.1rem 0.45rem; border-radius: var(--radius); margin-bottom: 0.6rem;
    background: var(--accent-dim); color: var(--accent);
}
.gcard-def { font-size: 0.9rem; color: var(--muted); line-height: 1.65; }
.gcard-ex {
    font-size: 0.82rem; color: var(--muted); line-height: 1.6;
    margin-top: 0.6rem; padding-top: 0.6rem;
    border-top: 1px dashed var(--line);
    font-style: italic;
}

/* ── Sidebar labels & separators ── */
.sb-label {
    font-size: 0.7rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.09em;
    color: var(--accent); margin-bottom: 0.25rem; display: block;
}
.sb-gap {
    border-top: 1px solid var(--line);
    margin: 1.1rem 0 0.9rem 0;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.55rem; }
</style>
"""


def inject_css():
    st.markdown(_CSS, unsafe_allow_html=True)


def brief_html(title, meta, items):
    """One line of HTML for the in-brief strip. items are (html, tone) pairs;
    the html is trusted markup built by the app from its own numbers."""
    rows = "".join(
        f'<div class="brief-item" role="listitem"><span class="brief-dot brief-dot-{tone}" '
        f'aria-hidden="true"></span><span>{text}</span></div>'
        for text, tone in items
    )
    return (f'<section class="brief" aria-label="{title}"><div class="brief-head">'
            f'<span class="brief-title">{title}</span><span class="brief-vs">{meta}</span></div>'
            f'<div role="list">{rows}</div></section>')

