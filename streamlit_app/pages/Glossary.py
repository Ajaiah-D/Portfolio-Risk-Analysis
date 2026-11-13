import sys

import streamlit as st

sys.path.insert(0, ".")
from streamlit_app import style

st.set_page_config(
    page_title="Glossary | Portfolio Risk Analysis",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Shared card styles; light/dark itself is Streamlit's native theme.
style.inject_css()
# Definitions read better at a narrower measure than the dashboard.
st.markdown("<style>.block-container { max-width: 1100px; }</style>", unsafe_allow_html=True)

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
    "Your collection of investments, meaning the group of stocks and ETFs you're analysing together. "
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
    "A reference point to compare your portfolio against. This tool always uses SPY, the S&P 500 ETF, "
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
    "Divides your money evenly across every holding. "
    "If you pick 5 stocks, each gets 20% of the total. This is the simplest approach. "
    "It doesn't try to predict which stock will do best. It's the tool's default mode.",
)
card(
    "Custom Weighting",
    "Basic",
    "Instead of splitting evenly, you enter the actual dollar amount you hold in each position. "
    "Every metric and chart then describes <i>your real portfolio</i>, not a hypothetical equal split. "
    "Switch to 'Custom amounts ($)' in the sidebar to use it.",
    "If you hold $6,000 of QQQ and $2,000 of XOM, QQQ drives 3× more of your risk and return."
)

# ── Risk & Volatility ────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Risk</div>', unsafe_allow_html=True)
st.markdown('<div class="section-heading">Risk & Volatility</div>', unsafe_allow_html=True)
st.markdown('<hr class="section-rule"/>', unsafe_allow_html=True)

card(
    "Volatility",
    "Risk",
    "How much a stock's price jumps around day to day. High volatility means big swings: "
    "the price might rise or fall sharply in a short time. Low volatility means the price moves more steadily. "
    "Volatility is measured by standard deviation of daily returns.",
    "A stock that swings ±5% per day is far more volatile than one that moves ±0.5% per day."
)
card(
    "Risk-Free Rate",
    "Risk",
    "The return you could earn without taking any risk, typically the interest rate on short-term US government bonds (T-bills). "
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
    "On your worst days, meaning the bottom 5% of all trading days, how much would you typically lose? "
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
card(
    "Underwater (Drawdown) Chart",
    "Risk",
    "Shows how far below its previous peak your portfolio was at every point in time. "
    "The depth of each dip is how bad the loss got; the width is how long it took to recover. "
    "A portfolio spending long stretches 'underwater' tests your patience even if it recovers eventually.",
    "A dip reaching −20% that takes a year to climb back to zero means 12 months of watching your money sit below its high."
)
card(
    "Rolling Volatility",
    "Risk",
    "Volatility measured over a sliding window (about 3 months) instead of the whole period. "
    "It shows <i>when</i> your portfolio was calm and when it was turbulent. "
    "a single overall number can hide the fact that most of the risk happened in one short stretch.",
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
    "A Sharpe of 1.5 means you earned 1.5 units of return for every unit of risk. A solid result."
)
card(
    "Sortino Ratio",
    "Performance",
    "Similar to the Sharpe ratio, but it only penalises downward price swings, not upward ones. "
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
card(
    "Rolling Beta",
    "Performance",
    "Beta measured over a sliding window so you can see how your portfolio's market sensitivity changed over time. "
    "A portfolio can average a Beta of 1.0 while actually swinging between defensive (0.7) and aggressive (1.3) phases.",
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
    "The bold line on the chart is your weighted portfolio; the dotted line is SPY.",
    "A cumulative return of 80% over 5 years means the investment more than doubled after 5 years."
)
card(
    "Efficient Frontier",
    "Chart",
    "A scatter plot showing 2,500 randomly weighted versions of your portfolio, each dot representing a "
    "different way to split your money across your chosen stocks. "
    "Dots toward the upper-left are best: higher return for lower risk. "
    "The star shows where your current weights sit in comparison; the marked points show the "
    "Max Sharpe and Min Volatility reference mixes. "
    "All of it describes the past, not the future. Treat it as a study aid, not a recommendation.",
)
card(
    "Max Sharpe / Min Volatility",
    "Chart",
    "Two reference allocations the tool finds from your holdings' history: "
    "the weighting that would have delivered the best risk-adjusted return (Max Sharpe), and the weighting "
    "that would have been the calmest ride (Min Volatility). "
    "They show what the <i>same holdings</i> could look like with different weights, "
    "but past-optimal weights are not guaranteed to be future-optimal.",
)
card(
    "Monte Carlo Simulation",
    "Chart",
    "Simulates a thousand possible futures for your portfolio by repeatedly rolling dice weighted by its "
    "historical average return and volatility. The result is a <i>range</i> of outcomes (median, optimistic, pessimistic) "
    "and the probability of reaching a target value. It assumes returns are normally distributed, "
    "which understates extreme events, so treat the tails with skepticism.",
    "'65% probability of reaching $50,000 in 10 years' means: in 650 of the 1,000 simulated futures, you got there."
)
card(
    "Correlation Matrix",
    "Chart",
    "Shows how closely each pair of stocks move together. "
    "A value near 1.0 means they tend to rise and fall at the same time. "
    "A value near 0 means they move independently. "
    "A negative value means they tend to move in opposite directions. "
    "Lower correlation between your holdings generally means better diversification: "
    "if one stock falls, the others aren't as likely to fall with it.",
    "AAPL and MSFT might have a correlation of 0.85, so they tend to move together. "
    "Gold (GLD) and tech stocks might have a correlation near 0, moving independently of each other."
)
card(
    "Diversification",
    "Chart",
    "The practice of spreading your investments across different stocks, sectors, or asset types "
    "so that a bad day for one doesn't sink your whole portfolio. "
    "Holding 10 unrelated stocks is less risky than holding 10 stocks that all do the same thing.",
)
card(
    "Diversification Score",
    "Chart",
    "A 0–100 score combining two things: how independently your holdings move (average correlation) "
    "and how evenly your money is spread (effective positions). "
    "All-tech portfolios score low because tech stocks move together; mixing in bonds, gold, or "
    "international funds raises the score because they move to a different rhythm.",
    "Five tech stocks might score 15. The same money across tech, healthcare, energy, and a bond ETF might score 60+."
)
card(
    "Effective Positions",
    "Chart",
    "How many truly independent positions your portfolio behaves like, once weights are accounted for. "
    "Ten holdings where one position is 80% of the money behaves like ~1.5 positions, not 10. "
    "The closer this number is to your actual holding count, the more evenly your risk is spread.",
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
