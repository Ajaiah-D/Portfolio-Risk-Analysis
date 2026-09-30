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

    /* Accents: mid-tones that hold contrast on both backgrounds. */
    --pink:       #fc88e5;
    --pink-dim:   rgba(252,136,229,0.14);
    --good:       #10b981;
    --good-dim:   rgba(16,185,129,0.14);
    --warn:       #f59e0b;
    --warn-dim:   rgba(245,158,11,0.14);
    --risk:       #f43f5e;
    --risk-dim:   rgba(244,63,94,0.14);
    --neutral:    #8b8cf8;
    --neutral-dim:rgba(139,140,248,0.14);
}

/* ── Page width ──
   layout="wide" still caps content with a max-width and wide side padding,
   which left large empty margins beside the sidebar. Let content use the
   available width, with a cap only for very wide monitors. */
.block-container {
    padding: 2rem 2.5rem 3rem 2.5rem;
    max-width: 1800px;
    animation: pageFade 0.35s ease-out;
}
@media (max-width: 640px) {
    .block-container { padding-left: 1rem; padding-right: 1rem; }
}
@keyframes pageFade {
    from { opacity: 0; transform: translateY(4px); }
    to   { opacity: 1; transform: none; }
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
.hero-title span {
    background: linear-gradient(92deg, var(--pink) 20%, var(--neutral) 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    color: var(--pink); /* fallback */
}
.hero-sub {
    font-size: 0.95rem; color: var(--muted);
    margin: 0 0 1.6rem 0; line-height: 1.65; max-width: 52rem;
}

/* ── Section headers ── */
.section-title {
    font-size: 0.72rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em;
    color: var(--pink);
    margin: 2.4rem 0 0.25rem 0;
}
.section-heading {
    font-size: 1.05rem; font-weight: 600;
    margin: 0 0 0.3rem 0;
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
    border: 1px solid var(--line);
    border-left: 3px solid var(--pink);
    border-radius: var(--radius);
    padding: 1rem 1.25rem;
    margin-bottom: 1.6rem;
    font-size: 0.84rem; line-height: 1.8;
}
.info-bar b { font-weight: 600; }

/* ── Insight cards ── */
.insight {
    background: var(--tint);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    padding: 0.9rem 1.15rem;
    margin-bottom: 0.5rem;
    font-size: 0.84rem; line-height: 1.6;
    transition: border-color 0.15s ease, transform 0.15s ease;
}
.insight:hover { transform: translateX(2px); }
.insight b { font-weight: 600; }
.insight-good { border-left: 3px solid var(--good); }
.insight-warn { border-left: 3px solid var(--warn); }
.insight-risk { border-left: 3px solid var(--risk); }
.insight-info { border-left: 3px solid var(--neutral); }
.insight-tag {
    display: inline-block; padding: 0.1rem 0.5rem; margin-right: 0.5rem;
    border-radius: var(--radius); font-size: 0.63rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.06em;
}

/* ── Scorecard row ── */
.scard, .mcard {
    background: var(--tint);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    box-shadow: 0 1px 4px var(--shadow);
    margin-bottom: 0.55rem;
    transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.scard { padding: 1rem 1.15rem; }
.mcard { padding: 1.25rem 1.35rem; }
.scard:hover, .mcard:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 18px var(--shadow);
    border-color: var(--pink);
}
.scard-label {
    font-size: 0.63rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em;
    color: var(--muted); margin-bottom: 0.25rem;
}
.scard-val {
    font-size: 1.35rem; font-weight: 700;
    line-height: 1.15;
}
.scard-sub {
    font-size: 0.74rem; color: var(--muted); margin-top: 0.2rem;
}
.scard-sub b { font-weight: 600; }
/* Optimizer scorecards reuse badge classes (.bg/.bb) for their value color;
   keep the color but drop the badge's tinted background. */
.scard-val.bg, .scard-val.bb { background: none; }
.pos { color: var(--good) !important; }
.neg { color: var(--risk) !important; }

/* ── Chips ── */
.chip {
    display: inline-block;
    background: var(--tint2); border: 1px solid var(--line);
    border-radius: var(--radius); padding: 0.12rem 0.5rem;
    font-size: 0.75rem; font-weight: 600; margin: 0.1rem;
}
.chip-bench {
    background: var(--pink-dim); border-color: var(--pink); color: var(--pink);
}

/* ── Metric cards ── */
.mcard-label {
    font-size: 0.67rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em;
    color: var(--muted); margin-bottom: 0.3rem;
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
.bp { background: var(--pink-dim);    color: var(--pink);    }

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
.rtag-bp { background: var(--pink-dim);    color: var(--pink);    }

/* ── Onboarding steps ── */
.step-card {
    background: var(--tint);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    padding: 1.3rem 1.4rem;
    min-height: 7.5rem;
    transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.step-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 18px var(--shadow);
    border-color: var(--pink);
}
.step-num {
    display: inline-block; width: 1.7rem; height: 1.7rem;
    border-radius: var(--radius);
    background: linear-gradient(135deg, var(--pink-dim), var(--neutral-dim));
    color: var(--pink);
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
    background: var(--pink-dim); color: var(--pink);
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
    color: var(--pink); margin-bottom: 0.25rem; display: block;
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
