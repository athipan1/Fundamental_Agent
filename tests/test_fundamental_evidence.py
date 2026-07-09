from app.fundamental_agent import attach_financial_evidence
from app.fundamental_evidence import build_fundamental_evidence
from app.models import Action, FundamentalAnalysisData


def _analysis_result():
    return {
        "score": 0.74,
        "analysis_source": "fundamental_engine_v2",
        "score_details": {
            "quality_score": 0.82,
            "growth_score": 0.61,
            "valuation_score": 0.76,
            "financial_health_score": 0.79,
            "cash_flow_score": 0.84,
        },
        "sector": "Financial Services",
        "risk_flags": [],
        "key_metrics": {
            "roe": 0.18,
            "roa": 0.04,
            "roic": 0.12,
            "profit_margins": 0.16,
            "revenue_3y_cagr": 0.09,
            "eps_3y_cagr": 0.11,
            "fcf_3y_cagr": 0.10,
            "pe_ratio": 12,
            "forward_pe": 11,
            "pb_ratio": 1.3,
            "debt_to_equity": 50,
            "operating_cash_flow": 1_200_000,
            "free_cash_flow": 900_000,
            "market_cap": 15_000_000_000,
            "dividend_yield": 3.5,
        },
    }


def test_build_fundamental_evidence_is_versioned_and_non_binding():
    evidence = build_fundamental_evidence(
        _analysis_result(),
        data_quality_score=0.92,
        style="value",
    )

    assert evidence["evidence_version"] == "fundamental-evidence-v1"
    assert evidence["bucket_decision_authority"] == "manager"
    assert evidence["manager_decision_required"] is True
    assert evidence["strategy_bucket_hint"] is None
    assert evidence["raw_scores"]["quality_score"] == 0.82
    assert evidence["raw_scores"]["fundamental_score"] == 0.74
    assert evidence["raw_scores"]["dividend_yield"] == 0.035
    assert evidence["raw_scores"]["debt_to_equity"] == 0.5
    assert evidence["provenance"]["analysis_source"] == "fundamental_engine_v2"
    assert evidence["provenance"]["style"] == "value"


def test_build_fundamental_evidence_marks_sparse_payload_insufficient():
    evidence = build_fundamental_evidence(
        {
            "score": 0.40,
            "score_details": {"quality_score": 0.50},
            "key_metrics": {},
            "risk_flags": ["fundamental_metrics_sparse"],
        },
        data_quality_score=0.30,
        style="growth",
    )

    assert evidence["evidence_status"] == "insufficient"
    assert evidence["evidence_completeness_score"] < 0.45
    assert "pe_ratio" in evidence["missing_critical_metrics"]
    assert "free_cash_flow" in evidence["missing_critical_metrics"]
    assert evidence["risk_flags"] == ["fundamental_metrics_sparse"]


def test_analysis_model_auto_populates_manager_consumable_raw_scores():
    result = _analysis_result()
    scores = result["score_details"]
    data = FundamentalAnalysisData(
        action=Action.BUY,
        confidence_score=0.74,
        raw_confidence_score=0.74,
        data_quality_score=0.92,
        reason="test",
        source="fundamental_engine_v2",
        quality_score=scores["quality_score"],
        growth_score=scores["growth_score"],
        valuation_score=scores["valuation_score"],
        financial_health_score=scores["financial_health_score"],
        cash_flow_score=scores["cash_flow_score"],
        sector=result["sector"],
        risk_flags=result["risk_flags"],
        key_metrics=result["key_metrics"],
    )

    assert data.fundamental_evidence is not None
    assert data.fundamental_evidence.evidence_version == "fundamental-evidence-v1"
    assert data.raw_scores["fundamental_score"] == 0.74
    assert data.raw_scores["pe_ratio"] == 12.0
    assert data.raw_scores["free_cash_flow"] == 900000.0
    assert data.manager_decision_required is True
    assert data.bucket_decision_authority == "manager"
    assert data.fundamental_evidence.strategy_bucket_hint is None


def test_attach_financial_evidence_preserves_dividend_and_provenance():
    analysis = {
        "score": 0.70,
        "score_details": {
            "quality_score": 0.75,
            "growth_score": 0.55,
            "valuation_score": 0.72,
            "financial_health_score": 0.70,
            "cash_flow_score": 0.80,
        },
        "key_metrics": {"pe_ratio": 14},
    }
    financial_data = {
        "Dividend Yield": 0.028,
        "Free Cash Flow": 500000,
        "Debt to Equity Ratio": 0.8,
        "Sector": "Consumer Defensive",
        "Industry": "Beverages",
        "Exchange": "NASDAQ",
        "Currency": "USD",
    }

    enriched = attach_financial_evidence(analysis, financial_data)

    assert enriched["key_metrics"]["pe_ratio"] == 14
    assert enriched["key_metrics"]["dividend_yield"] == 0.028
    assert enriched["key_metrics"]["free_cash_flow"] == 500000
    assert enriched["financial_data_provenance"]["provider"] == "yfinance_yahoo_quote"
    assert enriched["financial_data_provenance"]["sector"] == "Consumer Defensive"
    assert enriched["strategy_bucket_hint"] is None
    assert enriched["bucket_decision_authority"] == "manager"
