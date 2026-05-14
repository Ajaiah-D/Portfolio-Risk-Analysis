import streamlit as st

st.set_page_config(
    page_title="Glossary — Portfolio Risk Analysis",
    layout="wide",
    initial_sidebar_state="expanded",
)

dark = st.session_state.get("dark_mode", False)

if dark:
    _vars = """
    --bg:      #0c0c0c; --bg2: #141414; --bg3: #1c1c1c;
    --text:    #f0f0f0; --text2: #888888; --border: #272727;
    --card:    #141414; --shadow: rgba(0,0,0,0.35);
    """
else:
    _vars = """
    --bg:      #ffffff; --bg2: #f7f7f7; --bg3: #eeeeee;
    --text:    #111111; --text2: #666666; --border: #e5e5e5;
    --card:    #ffffff; --shadow: rgba(0,0,0,0.06);
    """

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
:root {{ {_vars}
    --pink: #fc88e5; --pink-dim: rgba(252,136,229,0.12);
    --good: #10b981; --warn: #f59e0b; --risk: #f43f5e;
}}
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
#MainMenu, footer {{ visibility: hidden; }}
.block-container {{ padding-top: 2rem; padding-bottom: 3rem; max-width: 900px; }}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > section {{
    background-color: var(--bg) !important;
}}
[data-testid="stHeader"] {{ background-color: var(--bg) !important; border-bottom: 1px solid var(--border) !important; }}
[data-testid="stSidebar"] {{ background-color: var(--bg2) !important; border-right: 1px solid var(--border); }}
p, span, label, div, h1, h2, h3, h4, li {{ color: var(--text) !important; }}

.hero-title {{ font-size: 2rem; font-weight: 700; color: var(--text); letter-spacing: -0.5px; margin: 0 0 0.35rem 0; }}
.hero-title span {{ color: var(--pink); }}
.hero-sub {{ font-size: 0.9rem; color: var(--text2); margin: 0 0 2rem 0; line-height: 1.6; }}

.section-title {{
    font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.1em; color: var(--pink); margin: 2.4rem 0 0.25rem 0;
}}
.section-heading {{
    font-size: 1.05rem; font-weight: 600; color: var(--text); margin: 0 0 0.8rem 0;
}}
hr.section-rule {{ border: none; border-top: 1px solid var(--border); margin: 0.5rem 0 1.2rem 0; }}

.gcard {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 1.2rem 1.4rem;
    box-shadow: 0 1px 4px var(--shadow); margin-bottom: 0.75rem;
}}
.gcard-term {{
    font-size: 1rem; font-weight: 700; color: var(--text); margin-bottom: 0.3rem;
}}
.gcard-tag {{
    display: inline-block; font-size: 0.65rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.08em;
    padding: 0.1rem 0.45rem; border-radius: 4px; margin-bottom: 0.6rem;
    background: var(--pink-dim); color: var(--pink);
}}
.gcard-def {{ font-size: 0.88rem; color: var(--text2); line-height: 1.65; }}
.gcard-ex {{
    font-size: 0.8rem; color: var(--text2); line-height: 1.6;
    margin-top: 0.6rem; padding-top: 0.6rem;
    border-top: 1px dashed var(--border);
    font-style: italic;
}}
</style>
""", unsafe_allow_html=True)

# ── Header ──
st.markdown('<h1 class="hero-title">Financial <span>Glossary</span></h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="hero-sub">Plain-English definitions for every term used in this tool. '
    'No finance background required.</p>',
    unsafe_allow_html=True,
)


def card(term, tag, definition, example=None):
    ex_html = f'<div class="gcard-ex">Example: {example}</div>' if example else ""
    st.markdown(
        f'<div class="gcard">'
        f'  <div class="gcard-term">{term}</div>'
        f'  <div class="gcard-tag">{tag}</div>'
        f'  <div class="gcard-def">{definition}</div>'
        f'  {ex_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── The Basics ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Start Here</div>', unsafe_allow_html=True)
st.markdown('<div class="section-heading">The Basics</div>', unsafe_allow_html=True)
st.markdown('<hr class="section-rule"/>', unsafe_allow_html=True)

card(
    "Stock (Equity)",
    "Basic",
    "A share of ownership in a company. When you buy a stock, you own a small piece of that business. "
    "If the company does well, the stock price tends to rise. If it does poorly, the price tends to fall.",
    "Buying one share of Apple (AAPL) makes you a part-owner of Apple Inc."
)
card(
    "Portfolio",
    "Basic",
    "Your collection of investments — the group of stocks and ETFs you're analysing together. "
    "A portfolio lets you spread risk across many companies rather than putting everything into one.",
    "A portfolio of AAPL, MSFT, and AMZN means you hold shares in all three."
)
card(
    "ETF (Exchange-Traded Fund)",
    "Basic",
    "A single investment that holds many stocks inside it, like a pre-made basket. "
    "Buying one ETF instantly gives you exposure to all the companies it contains. "
    "They trade on stock exchanges just like individual shares.",
    "SPY is an ETF that holds all 500 companies in the S&P 500 index."
)
card(
    "S&P 500",
    "Basic",
    "An index of the 500 largest publicly traded companies in the US. "
    "It's the most widely used measure of how the US stock market is doing overall.",
)
card(
    "Benchmark (SPY)",
    "Basic",
    "A reference point to compare your portfolio against. This tool always uses SPY — the S&P 500 ETF — "
    "as the benchmark. If your portfolio earns more than SPY with less risk, it's performing well. "
    "If it earns less, you'd have been better off just buying SPY.",
    "SPY returned 25% last year. If your portfolio returned 18%, you underperformed the benchmark."
)
card(
    "Return",
    "Basic",
    "How much money an investment made (or lost), expressed as a percentage. "
    "A daily return is how much the price changed in a single day. "
    "Cumulative return is the total gain or loss over the whole period.",
    "A stock that goes from $100 to $110 has a 10% return."
)
card(
    "Equal Weighting",
    "Basic",
    "This tool divides your money evenly across every stock in your portfolio. "
    "If you pick 5 stocks, each gets 20% of the total. This is the simplest approach — "
    "it doesn't try to predict which stock will do best.",
)

# ── Risk & Volatility ────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Risk</div>', unsafe_allow_html=True)
st.markdown('<div class="section-heading">Risk & Volatility</div>', unsafe_allow_html=True)
st.markdown('<hr class="section-rule"/>', unsafe_allow_html=True)

card(
    "Volatility",
    "Risk",
    "How much a stock's price jumps around day to day. High volatility means big swings — "
    "the price might rise or fall sharply in a short time. Low volatility means the price moves more steadily. "
    "Volatility is measured by standard deviation of daily returns.",
    "A stock that swings ±5% per day is far more volatile than one that moves ±0.5% per day."
)
card(
    "Risk-Free Rate",
    "Risk",
    "The return you could earn without taking any risk — typically the interest rate on short-term US government bonds (T-bills). "
    "It's used as a baseline: any investment that takes on risk should ideally beat this rate, otherwise why bother?",
    "If T-bills pay 5% and your portfolio earns 4%, you'd have been better off with no risk at all."
)
card(
    "Max Drawdown",
    "Risk",
    "The biggest drop from a peak to a low point over the selected period, shown as a percentage. "
    "It answers: 'What's the worst loss I would have sat through if I'd held this the whole time?' "
    "A smaller (less negative) number is better.",
    "A max drawdown of −30% means the investment fell 30% from its highest point before recovering."
)
card(
    "Value at Risk (VaR, 5%)",
    "Risk",
    "On your worst days — specifically the bottom 5% of all trading days — how much would you typically lose? "
    "VaR gives you a threshold: 95% of days, your loss should be smaller than this number. "
    "It's based purely on past returns, so it's only as reliable as history.",
    "A VaR of −2% means on your worst days, you'd expect to lose about 2% or more."
)
card(
    "CVaR / Expected Shortfall",
    "Risk",
    "Takes VaR one step further: on the days that are already in that worst 5%, what's the average loss? "
    "It describes what a bad day actually looks like on average, not just the cutoff. "
    "CVaR is always a larger loss than VaR.",
    "If VaR is −2%, a CVaR of −3% means that when bad days happen, the average loss is 3%."
)

# ── Performance Metrics ─────────────────────────────────────────────────────
st.markdown('<div class="section-title">Performance</div>', unsafe_allow_html=True)
st.markdown('<div class="section-heading">Performance Metrics</div>', unsafe_allow_html=True)
st.markdown('<hr class="section-rule"/>', unsafe_allow_html=True)

card(
    "Sharpe Ratio",
    "Performance",
    "Measures how much return you're getting for each unit of risk you're taking. "
    "A higher Sharpe ratio means you're being better rewarded for the risk. "
    "It uses total volatility (all price swings, up and down) in the calculation. "
    "Above 1.0 is generally considered good; above 2.0 is exceptional.",
    "A Sharpe of 1.5 means you earned 1.5 units of return for every unit of risk — a solid result."
)
card(
    "Sortino Ratio",
    "Performance",
    "Similar to the Sharpe ratio, but it only penalises downward price swings — not upward ones. "
    "The logic is that big gains aren't really 'risk', so why count them against you? "
    "Sortino tends to paint a more favourable picture than Sharpe for investments that occasionally spike upward.",
    "A stock that often surges but rarely crashes will score better on Sortino than Sharpe."
)
card(
    "Beta",
    "Performance",
    "Measures how much a stock moves relative to the overall market (SPY). "
    "Beta of 1.0 = moves in line with the market. "
    "Beta above 1 = amplifies market moves (riskier but potentially higher returns). "
    "Beta below 1 = more stable than the market. "
    "Beta below 0 = tends to move opposite to the market.",
    "A Beta of 1.5 means when the market drops 10%, this stock tends to drop 15%."
)

# ── Charts & Analysis ────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Charts</div>', unsafe_allow_html=True)
st.markdown('<div class="section-heading">Charts & Analysis</div>', unsafe_allow_html=True)
st.markdown('<hr class="section-rule"/>', unsafe_allow_html=True)

card(
    "Cumulative Return",
    "Chart",
    "Shows the total growth of $1 invested at the start of the period. "
    "If the line is at 50%, a $1,000 investment would now be worth $1,500. "
    "The bold line on the chart is your equal-weight portfolio; the dotted line is SPY.",
    "A cumulative return of 80% over 5 years means the investment more than doubled after 5 years."
)
card(
    "Efficient Frontier",
    "Chart",
    "A scatter plot showing 2,500 randomly weighted versions of your portfolio, each dot representing a "
    "different way to split your money across your chosen stocks. "
    "Dots toward the upper-left are best — higher return for lower risk. "
    "Your equal-weight portfolio (the star) shows where your current split sits in comparison. "
    "This is a visualisation, not a recommendation — it doesn't tell you the 'best' weighting.",
)
card(
    "Correlation Matrix",
    "Chart",
    "Shows how closely each pair of stocks move together. "
    "A value near 1.0 means they tend to rise and fall at the same time. "
    "A value near 0 means they move independently. "
    "A negative value means they tend to move in opposite directions. "
    "Lower correlation between your holdings generally means better diversification — "
    "if one stock falls, the others aren't as likely to fall with it.",
    "AAPL and MSFT might have a correlation of 0.85 — they tend to move together. "
    "Gold (GLD) and tech stocks might have a correlation near 0 — they move independently."
)
card(
    "Diversification",
    "Chart",
    "The practice of spreading your investments across different stocks, sectors, or asset types "
    "so that a bad day for one doesn't sink your whole portfolio. "
    "Holding 10 unrelated stocks is less risky than holding 10 stocks that all do the same thing.",
)

# ── Sectors ──────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Universe</div>', unsafe_allow_html=True)
st.markdown('<div class="section-heading">Sectors (GICS)</div>', unsafe_allow_html=True)
st.markdown('<hr class="section-rule"/>', unsafe_allow_html=True)

card(
    "GICS Sector",
    "Classification",
    "The Global Industry Classification Standard groups companies into 11 broad sectors based on what they do. "
    "This tool lets you filter stocks by sector so you can build a diversified portfolio across industries, "
    "or focus on a specific part of the economy.",
    "Apple is in 'Information Technology'. JPMorgan is in 'Financials'. ExxonMobil is in 'Energy'."
)
