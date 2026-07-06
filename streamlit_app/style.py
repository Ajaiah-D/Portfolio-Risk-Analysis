"""CSS injection for the Streamlit app — all theming lives here.

Two blocks are injected:
1. A variable-driven block (light/dark swap via CSS custom properties).
2. A hardcoded popover/toolbar block, because Streamlit popovers render in a
   separate stacking context where :root variables do not resolve.
"""
import streamlit as st

_DARK_VARS = """
    --bg:      #0c0c0c;
    --bg2:     #141414;
    --bg3:     #1c1c1c;
    --text:    #f0f0f0;
    --text2:   #888888;
    --border:  #272727;
    --card:    #141414;
    --shadow:  rgba(0,0,0,0.35);
"""

_LIGHT_VARS = """
    --bg:      #ffffff;
    --bg2:     #f7f7f7;
    --bg3:     #eeeeee;
    --text:    #111111;
    --text2:   #666666;
    --border:  #e5e5e5;
    --card:    #ffffff;
    --shadow:  rgba(0,0,0,0.06);
"""


def inject_css(dark: bool):
    _vars = _DARK_VARS if dark else _LIGHT_VARS
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

/* ── Tabs ── */
[data-testid="stTabs"] button {{
    color: var(--text2) !important;
    font-weight: 600;
}}
[data-testid="stTabs"] button[aria-selected="true"] {{
    color: var(--pink) !important;
}}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
    background-color: var(--pink) !important;
}}
[data-testid="stTabs"] [data-baseweb="tab-border"] {{
    background-color: var(--border) !important;
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

/* ── Insight cards ── */
.insight {{
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.8rem 1.05rem;
    margin-bottom: 0.5rem;
    font-size: 0.82rem; color: var(--text2); line-height: 1.6;
}}
.insight b {{ color: var(--text); font-weight: 600; }}
.insight-good {{ border-left: 3px solid var(--good); }}
.insight-warn {{ border-left: 3px solid var(--warn); }}
.insight-risk {{ border-left: 3px solid var(--risk); }}
.insight-info {{ border-left: 3px solid var(--neutral); }}
.insight-tag {{
    display: inline-block; padding: 0.1rem 0.5rem; margin-right: 0.5rem;
    border-radius: 20px; font-size: 0.63rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.06em;
}}

/* ── Scorecard row ── */
.scard {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 0.85rem 1rem;
    box-shadow: 0 1px 4px var(--shadow);
    margin-bottom: 0.55rem;
}}
.scard-label {{
    font-size: 0.63rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em;
    color: var(--text2); margin-bottom: 0.25rem;
}}
.scard-val {{
    font-size: 1.35rem; font-weight: 700; color: var(--text);
    line-height: 1.15;
}}
.scard-sub {{
    font-size: 0.72rem; color: var(--text2); margin-top: 0.2rem;
}}
.scard-sub b {{ font-weight: 600; }}
.pos {{ color: var(--good) !important; }}
.neg {{ color: var(--risk) !important; }}

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
    display: flex; flex-wrap: wrap; gap: 0.28rem;
    margin-top: 0.5rem; padding-top: 0.45rem;
    border-top: 1px dashed var(--border);
}}
.rtag {{
    font-size: 0.63rem; padding: 0.13rem 0.42rem;
    border-radius: 4px; white-space: nowrap; line-height: 1.5;
}}
.rtag-bg {{ background: var(--good-dim);    color: var(--good);    }}
.rtag-by {{ background: var(--warn-dim);    color: var(--warn);    }}
.rtag-br {{ background: var(--risk-dim);    color: var(--risk);    }}
.rtag-bb {{ background: var(--neutral-dim); color: var(--neutral); }}
.rtag-bp {{ background: var(--pink-dim);    color: var(--pink);    }}

/* ── Onboarding steps ── */
.step-card {{
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.1rem 1.2rem;
    min-height: 7.5rem;
}}
.step-num {{
    display: inline-block; width: 1.6rem; height: 1.6rem;
    border-radius: 50%; background: var(--pink-dim); color: var(--pink);
    font-weight: 700; font-size: 0.8rem; text-align: center; line-height: 1.6rem;
    margin-bottom: 0.5rem;
}}
.step-title {{ font-size: 0.9rem; font-weight: 600; color: var(--text); margin-bottom: 0.25rem; }}
.step-desc {{ font-size: 0.78rem; color: var(--text2); line-height: 1.5; }}

/* ── Dataframe toolbar (three-dot menu) — base ── */
[data-testid="stElementToolbar"] {{
    background: var(--bg2) !important;
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

    # Popovers render in a separate stacking context where :root vars may not
    # resolve — hardcode both palettes.
    if dark:
        st.markdown(
            """
<style>
[data-testid="stElementToolbarButton"] svg,
[data-testid="stElementToolbarButton"] button,
[data-testid="stElementToolbar"] svg,
[data-testid="stHeader"] svg,
[data-testid="stToolbar"] svg {
    color:  #e8e8e8 !important;
    fill:   #e8e8e8 !important;
    stroke: #e8e8e8 !important;
    opacity: 1 !important;
}
[data-testid="stBasePopoverContent"] {
    background-color: #1c1c1c !important;
    border: 1px solid #2a2a2a !important;
}
[data-testid="stBasePopoverContent"] *,
[data-testid="stBasePopoverContent"] li,
[data-testid="stBasePopoverContent"] button,
[data-testid="stBasePopoverContent"] span,
[data-testid="stBasePopoverContent"] p {
    background-color: #1c1c1c !important;
    color: #e8e8e8 !important;
}
[data-testid="stBasePopoverContent"] li:hover,
[data-testid="stBasePopoverContent"] button:hover {
    background-color: #2a2a2a !important;
}
</style>
""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
<style>
[data-testid="stElementToolbarButton"] svg,
[data-testid="stElementToolbar"] svg {
    color:  #444444 !important;
    fill:   #444444 !important;
    stroke: #444444 !important;
    opacity: 1 !important;
}
[data-testid="stBasePopoverContent"] {
    background-color: #f7f7f7 !important;
    border: 1px solid #e5e5e5 !important;
}
[data-testid="stBasePopoverContent"] *,
[data-testid="stBasePopoverContent"] li,
[data-testid="stBasePopoverContent"] button,
[data-testid="stBasePopoverContent"] span,
[data-testid="stBasePopoverContent"] p {
    background-color: #f7f7f7 !important;
    color: #111111 !important;
}
[data-testid="stBasePopoverContent"] li:hover,
[data-testid="stBasePopoverContent"] button:hover {
    background-color: #eeeeee !important;
}
</style>
""",
            unsafe_allow_html=True,
        )
