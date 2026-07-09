from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_analyze_response_exposes_versioned_fundamental_evidence(monkeypatch):
    def fake_run_analysis(ticker, style, correlation_id=None):
        return {
            "strength": "buy",
            "score": 0.76,
            "reasoning": "deterministic test analysis",
            "source": "fundamental_agent",
            "analysis_source": "fundamental_engine_v2",
            "score_details": {
                "quality_score": 0.82,
                "growth_score": 0.64,
                "valuation_score": 0.78,
                "financial_health_score": 0.80,
                "cash_flow_score": 0.86,
            },
            "sector": "Consumer Defensive",
            "sector_weights": {},
            "risk_flags": [],
            "comparative_analysis": {},
            "key_metrics": {
                "roe": 0.21,
                "revenue_3y_cagr": 0.08,
                "eps_3y_cagr": 0.10,
                "fcf_3y_cagr": 0.09,
                "pe_ratio": 16,
                "pb_ratio": 2.1,
                "debt_to_equity": 0.6,
                "free_cash_flow": 1_500_000,
                "dividend_yield": 0.031,
            },
        }

    monkeypatch.setattr("app.main.run_analysis", fake_run_analysis)

    response = client.post(
        "/analyze",
        json={"ticker": "TEST", "style": "dividend"},
        headers={"X-Correlation-ID": "evidence-contract-test"},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "success"
    assert body["version"] == "1.1.0"
    assert body["correlation_id"] == "evidence-contract-test"
    assert body["data"]["evidence_version"] == "fundamental-evidence-v1"
    assert body["data"]["manager_decision_required"] is True
    assert body["data"]["bucket_decision_authority"] == "manager"
    assert body["data"]["raw_scores"]["quality_score"] == 0.82
    assert body["data"]["raw_scores"]["dividend_yield"] == 0.031
    assert body["data"]["fundamental_evidence"]["strategy_bucket_hint"] is None
    assert body["data"]["fundamental_evidence"]["provenance"]["analysis_source"] == "fundamental_agent"
