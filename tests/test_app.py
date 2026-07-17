"""Streamlit AppTest smoke tests — run the real app end-to-end headlessly.

These need the local price database, so they are skipped when it is absent
(e.g. on a fresh clone before ingestion).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from streamlit.testing.v1 import AppTest

APP = "streamlit_app/Portfolio_Analyzer.py"
DB = "data/portfolio_data.db"

pytestmark = pytest.mark.skipif(
    not os.path.exists(DB), reason="price database not present"
)


def make_app():
    return AppTest.from_file(APP, default_timeout=60)


def test_empty_state_renders():
    at = make_app().run()
    assert not at.exception
    # onboarding: example button present, no analysis yet
    assert any("example" in b.label.lower() for b in at.button)
    assert len(at.tabs) == 0


def test_example_portfolio_full_run():
    at = make_app().run()
    example_btn = next(b for b in at.button if "example" in b.label.lower())
    example_btn.click().run()
    assert not at.exception
    assert len(at.tabs) == 6
    # metric cards + insights are markdown blocks; sanity check content exists
    all_md = " ".join(str(m.value) for m in at.markdown)
    assert "Sharpe" in all_md
    assert "mcard" in all_md
    assert "insight" in all_md


def test_run_with_manual_selection():
    at = make_app()
    at.session_state["holdings_sel"] = []
    at.run()
    # pick a stock and an ETF from the unified picker (labels match universe format)
    opts = at.multiselect(key="holdings_sel").options
    labels = [o for o in opts if o.startswith("AAPL")][:1] + [o for o in opts if o.startswith("QQQ")][:1]
    assert len(labels) == 2, "unified picker should offer both stocks and ETFs"
    at.multiselect(key="holdings_sel").set_value(labels)
    run_btn = next(b for b in at.button if "Run Analysis" in b.label)
    run_btn.click().run()
    assert not at.exception
    assert len(at.tabs) == 6


def test_url_prefill_autoruns():
    at = make_app()
    at.query_params["t"] = "AAPL,MSFT,JNJ"
    at.query_params["h"] = "3"
    at.query_params["r"] = "4"
    at.run()
    assert not at.exception
    assert len(at.tabs) == 6
    assert at.session_state["horizon"] == "3Y"
    assert at.session_state["rfr_pct"] == 4.0


def test_glossary_page_renders():
    at = AppTest.from_file("streamlit_app/pages/Glossary.py", default_timeout=30).run()
    assert not at.exception
    all_md = " ".join(str(m.value) for m in at.markdown)
    for term in ("Sharpe Ratio", "Monte Carlo", "Diversification Score", "Rolling Beta"):
        assert term in all_md


def test_custom_amounts_mode():
    at = make_app()
    at.query_params["t"] = "AAPL,MSFT"
    at.query_params["a"] = "3000,1000"
    at.run()
    assert not at.exception
    assert at.session_state["wmode"] == "Custom amounts ($)"
    assert len(at.tabs) == 6
    # custom mode derives portfolio value -> Planning tab should have MC inputs
    all_md = " ".join(str(m.value) for m in at.markdown)
    assert "Dollar Context" in all_md


def _planning_info_bar(at):
    """The Monte Carlo results info bar ('% probability of reaching ...')."""
    return next(str(m.value) for m in at.markdown if "of reaching" in str(m.value))


def test_planning_recalculates_on_input_change():
    at = make_app()
    at.query_params["t"] = "AAPL,MSFT,JNJ"
    at.query_params["v"] = "10000"
    at.run()
    assert not at.exception
    before = _planning_info_bar(at)

    # Change the Monte Carlo years slider -> results must recompute
    years = next(s for s in at.slider if "years" in s.label.lower())
    years.set_value(25).run()
    assert not at.exception
    after_years = _planning_info_bar(at)
    assert after_years != before, "MC results did not change when years changed"

    # Change the sidebar time horizon -> return series changes -> recompute
    at.session_state["horizon"] = "1Y"
    at.run()
    assert not at.exception
    after_horizon = _planning_info_bar(at)
    assert after_horizon != after_years, "MC results did not change when horizon changed"


def test_budget_mode_equal_start(monkeypatch=None):
    # Custom mode + portfolio value: amounts should start as an equal split
    at = make_app()
    at.query_params["t"] = "AAPL,MSFT,JNJ,XOM"
    at.run()
    at.session_state["wmode"] = "Custom amounts ($)"
    at.session_state["pv"] = 5
    at.run()
    assert not at.exception
    amounts = at.session_state["amounts"]
    assert set(amounts) == {"AAPL", "MSFT", "JNJ", "XOM"}
    assert sum(amounts.values()) == pytest.approx(5.0, abs=0.01)
    assert all(abs(v - 1.25) < 0.011 for v in amounts.values())
