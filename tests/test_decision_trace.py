from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

from app.fundamental_engine_v2 import run_fundamental_v2, weighted_average, action_from_score
from app.fundamental_agent import _merge_llm_reasoning, run_analysis
from app.main import TickerRequest, _run_analysis_result, _to_response_data
from app.scanner_financial_inputs import prefetched_financial_data


def strong_financials():
    return {
        "Sector": "Technology",
        "ROE": 0.3,
        "ROA": 0.2,
        "ROIC": 0.3,
        "Profit Margins": 0.3,
        "Operating Margin": 0.3,
        "Gross Margin": 0.6,
        "FCF Margin": 0.25,
        "Cash Conversion": 1.1,
        "Interest Coverage": 12,
        "EPS": 6,
        "Market Cap": 100e9,
        "Operating Cash Flow": 12e9,
        "Free Cash Flow": 10e9,
        "Net Cash": 10e9,
        "Debt to Equity Ratio": 0.2,
        "P/E Ratio": 20,
        "Forward P/E": 18,
        "PEG Ratio": 0.4,
        "P/B Ratio": 0.7,
        "Enterprise Value": 100e9,
        "EBITDA": 10e9,
        "Total Revenue": 40e9,
        "Revenue Growth": 0.3,
        "EPS Growth": 0.3,
        "FCF Growth": 0.3,
        "Quarterly Revenue Growth": 0.12,
        "Quarterly EPS Growth": 0.12,
        "Quarterly FCF Growth": 0.12,
    }


def test_buy_from_financial_evidence_and_severe_flag_veto():
    result = run_fundamental_v2("TEST", strong_financials())
    assert result["strength"] == "buy"
    trace = result["decision_trace"]
    assert all(item["passed"] for item in trace["buy_conditions"])
    assert sum(item["contribution"] for item in trace["score_components"].values()) == pytest.approx(
        result["score"], abs=0.00005
    )
    rejected = run_fundamental_v2("TEST", {**strong_financials(), "Operating Cash Flow": -1})
    assert rejected["strength"] != "buy"
    assert "negative_operating_cash_flow" in rejected["risk_flags"]
    assert action_from_score(0.7199, []) != "buy"
    assert action_from_score(0.72, []) == "buy"


def test_scanner_decimal_growth_is_never_scaled_or_synthetically_annualized():
    data = prefetched_financial_data(
        {
            "symbol": "QTTB",
            "raw_scores": {
                "revenue_3y_cagr": 1.0066062308098753,
                "eps_growth": 5.9485,
                "fcf_growth": 3.8568,
                "roe": 30,
                "roa": 0.8,
                "profit_margins": 20,
                "free_cash_flow": 100,
                "debt_to_equity": 15,
            },
        }
    )
    result = run_fundamental_v2("QTTB", data)
    assert result["key_metrics"]["revenue_3y_cagr"] == pytest.approx(1.0066062308098753)
    assert result["key_metrics"]["eps_3y_cagr"] is None  # total growth is not annual CAGR
    assert result["key_metrics"]["fcf_3y_cagr"] is None
    assert result["key_metrics"]["roe"] == 0.30
    assert result["key_metrics"]["roa"] == 0.008
    assert result["key_metrics"]["operating_cash_flow"] is None
    assert result["key_metrics"]["debt_to_equity"] == 15
    assert "Historical Revenue" not in data


def test_real_zero_growth_and_zero_score_keep_their_weight():
    assert weighted_average([(1, 0.1), (0, 0.9)]) == 0.1
    result = run_fundamental_v2(
        "TEST", {"Historical Revenue": {"2024-12-31": 100, "2025-12-31": 100}, "Revenue Growth": 0.5}
    )
    assert result["key_metrics"]["revenue_3y_cagr"] == 0


def test_llm_cannot_override_direction_or_score():
    result = run_fundamental_v2("TEST", strong_financials())
    merged = _merge_llm_reasoning(result, {"strength": "sell", "score": 0.1, "source": "llm"})
    assert merged == result
    with (
        patch("app.fundamental_agent.cache_handler.load_from_cache", return_value=None),
        patch("app.fundamental_agent.cache_handler.save_to_cache"),
        patch("app.fundamental_agent.get_financial_data", return_value=strong_financials()),
        patch("app.fundamental_agent.analyze_financials", side_effect=RuntimeError("offline")),
    ):
        actual = run_analysis("TEST")
    assert actual["strength"] == result["strength"]
    assert actual["score"] == result["score"]


def test_valid_zero_growth_is_not_replaced_by_prefetch(monkeypatch):
    primary = {
        "strength": "neutral",
        "score": 0.4,
        "score_details": {"growth_score": 0},
        "key_metrics": {"revenue_3y_cagr": 0},
    }
    monkeypatch.setattr("app.main.run_analysis", lambda *args, **kwargs: primary)
    assert (
        _run_analysis_result(
            TickerRequest(ticker="TEST", prefetched_data={"raw_scores": {"revenue_3y_cagr": 0.8}})
        )
        is primary
    )


def test_observed_history_provenance_and_stale_payload_rejection():
    payload = {
        "schema_version": "scanner-financial-inputs.v1",
        "symbol": "TEST",
        "synthetic": False,
        "ratio_unit": "decimal",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "values": {"Historical Revenue": {"2022-12-31": 100, "2025-12-31": 172.8}},
    }
    context = {"symbol": "TEST", "metadata": {"data_bundle": {"financial_inputs": payload}}}
    values = prefetched_financial_data(context)
    assert values["Historical Revenue"] == payload["values"]["Historical Revenue"]
    result = run_fundamental_v2("TEST", values)
    # Missing intermediate fiscal years must not turn three-year growth into one-year growth.
    assert result["key_metrics"]["revenue_3y_cagr"] == pytest.approx(0.20, abs=0.0001)
    result["analysis_source"] = "fundamental_engine_v2_with_scanner_prefetch"
    response = _to_response_data(TickerRequest(ticker="TEST", prefetched_data=context), result)
    assert response.source == "fundamental_engine_v2_with_scanner_prefetch"
    assert response.fundamental_evidence.provenance["synthetic_or_prefetched"] is True
    payload["observed_at"] = (datetime.now(timezone.utc) - timedelta(hours=7)).isoformat()
    assert "Historical Revenue" not in prefetched_financial_data(context)
