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

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
    -webkit-font-smoothing: antialiased;
}}
#MainMenu, footer {{ visibility: hidden; }}
.block-container {{
    padding-top: 2rem; padding-bottom: 3rem; max-width: 1200px;
    animation: pageFade 0.35s ease-out;
}}
@keyframes pageFade {{
    from {{ opacity: 0; transform: translateY(4px); }}
    to   {{ opacity: 1; transform: none; }}
}}

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
    /* Streamlit's default drag-resized width is narrower than the Weighting
       and Time Horizon segmented controls need, so they wrap onto a second
       row instead of showing as one row of pills. min-width sets a floor
       without disabling the drag handle — users can still widen it further,
       just never narrower than this. */
    min-width: 380px !important;
}}

/* ── Sidebar page navigation (Portfolio Analyzer / Glossary links) ──
   Streamlit's built-in nav paints its own light-theme pill backgrounds on
   the links (resting, hover, and current-page states), which in dark mode
   puts white text on a near-white pill. Strip every background it draws so
   the themed sidebar shows through, then re-add hover/current styling with
   translucent colors that are readable over any background. */
[data-testid="stSidebarNav"],
[data-testid="stSidebarNav"] ul,
[data-testid="stSidebarNav"] li,
[data-testid="stSidebarNav"] li > div,
[data-testid="stSidebarNav"] a,
[data-testid="stSidebarNav"] a > div,
[data-testid="stSidebarNav"] a span {{
    background-color: transparent !important;
    color: var(--text) !important;
}}
[data-testid="stSidebarNav"] a:hover,
[data-testid="stSidebarNav"] a:hover > div {{
    background-color: var(--bg3) !important;
}}
[data-testid="stSidebarNav"] a:hover span {{
    color: var(--pink) !important;
}}
[data-testid="stSidebarNav"] a[aria-current="page"],
[data-testid="stSidebarNav"] a[aria-current="true"],
[data-testid="stSidebarNav"] a[aria-current="page"] > div {{
    background-color: var(--pink-dim) !important;
}}
[data-testid="stSidebarNav"] a[aria-current="page"] span,
[data-testid="stSidebarNav"] a[aria-current="true"] span {{
    color: var(--pink) !important;
}}
[data-testid="stSidebarNav"] svg {{
    color: var(--text2) !important;
    fill: var(--text2) !important;
}}
[data-testid="stSidebarNavSeparator"] {{
    border-color: var(--border) !important;
}}
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stSidebarCollapsedControl"] svg {{
    color: var(--text2) !important;
    fill: var(--text2) !important;
}}

/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    gap: 0.35rem;
}}
[data-testid="stTabs"] button {{
    color: var(--text2) !important;
    font-weight: 600;
    font-size: 0.88rem;
    padding: 0.55rem 0.9rem;
    border-radius: 8px 8px 0 0;
    transition: color 0.15s ease, background 0.15s ease;
}}
[data-testid="stTabs"] button:hover {{
    color: var(--text) !important;
    background: var(--bg2);
}}
[data-testid="stTabs"] button[aria-selected="true"] {{
    color: var(--pink) !important;
}}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
    background-color: var(--pink) !important;
    height: 2.5px;
    border-radius: 2px;
}}
[data-testid="stTabs"] [data-baseweb="tab-border"] {{
    background-color: var(--border) !important;
}}

/* ── Buttons ── */
.stButton > button, [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-secondary"] {{
    border-radius: 9px !important;
    font-weight: 600 !important;
    transition: transform 0.12s ease, box-shadow 0.12s ease, filter 0.12s ease;
}}
.stButton > button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 4px 14px var(--shadow);
    filter: brightness(1.03);
}}
.stButton > button:active {{ transform: translateY(0); }}
[data-testid="stBaseButton-primary"] {{ color: #ffffff !important; }}

/* ── Inputs: soften corners ── */
[data-baseweb="select"] > div,
[data-baseweb="input"],
[data-testid="stNumberInput"] div[data-baseweb="input"] {{
    border-radius: 9px !important;
}}

/* ── Segmented controls (weighting, time horizon) ── */
[data-testid="stSegmentedControl"] button {{
    background-color: var(--bg3) !important;
    color: var(--text2) !important;
    border-color: var(--border) !important;
    font-weight: 600;
}}
[data-testid="stSegmentedControl"] button p {{
    color: inherit !important;
    font-size: 0.8rem !important;
}}
[data-testid="stSegmentedControl"] button[aria-checked="true"],
[data-testid="stSegmentedControl"] button[kind="segmented_controlActive"] {{
    background-color: var(--pink-dim) !important;
    color: var(--pink) !important;
    border-color: var(--pink) !important;
}}

/* ── Typography ── */
.hero-title {{
    font-size: 2.3rem; font-weight: 700; color: var(--text);
    letter-spacing: -0.8px; margin: 0 0 0.35rem 0;
}}
.hero-title span {{
    background: linear-gradient(92deg, var(--pink) 20%, var(--neutral) 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    color: var(--pink); /* fallback */
}}
.hero-sub {{
    font-size: 0.92rem; color: var(--text2);
    margin: 0 0 1.6rem 0; line-height: 1.65; max-width: 46rem;
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
    border-radius: 13px;
    padding: 0.85rem 1rem;
    box-shadow: 0 1px 4px var(--shadow);
    margin-bottom: 0.55rem;
    transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}}
.scard:hover {{
    transform: translateY(-2px);
    box-shadow: 0 6px 18px var(--shadow);
    border-color: var(--pink);
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
    border-radius: 13px;
    padding: 1.1rem 1.2rem;
    box-shadow: 0 1px 4px var(--shadow);
    margin-bottom: 0.55rem;
    transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}}
.mcard:hover {{
    transform: translateY(-2px);
    box-shadow: 0 6px 18px var(--shadow);
    border-color: var(--pink);
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
    border-radius: 13px;
    padding: 1.15rem 1.25rem;
    min-height: 7.5rem;
    transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}}
.step-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 6px 18px var(--shadow);
    border-color: var(--pink);
}}
.step-num {{
    display: inline-block; width: 1.7rem; height: 1.7rem;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--pink-dim), var(--neutral-dim));
    color: var(--pink);
    font-weight: 700; font-size: 0.8rem; text-align: center; line-height: 1.7rem;
    margin-bottom: 0.55rem;
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
    color: var(--pink); margin-bottom: 0.25rem; display: block;
}}

/* ── Sidebar section separator (replaces heavy --- rules) ── */
.sb-gap {{
    border-top: 1px solid var(--border);
    margin: 1.1rem 0 0.9rem 0;
}}

/* ── Sidebar: tighten vertical rhythm ── */
[data-testid="stSidebar"] .block-container {{ padding-top: 1.2rem; }}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: 0.55rem; }}

/* ── Insight cards: gentle hover ── */
.insight {{
    transition: border-color 0.15s ease, transform 0.15s ease;
}}
.insight:hover {{ transform: translateX(2px); }}
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
