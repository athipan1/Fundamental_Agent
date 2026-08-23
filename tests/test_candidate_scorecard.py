from app.candidate_scorecard import build_fundamental_candidate_scorecard
from app.fundamental_evidence import build_fundamental_evidence


def test_fundamental_candidate_scorecard_awards_five_explainable_points():
    scorecard = build_fundamental_candidate_scorecard(
        {
            "revenue_growth": 0.18,
            "eps_growth": 0.22,
            "free_cash_flow": 1_000_000,
            "debt_to_equity": 0.40,
            "roic": 0.16,
        },
        sector="Technology",
        evidence_status="complete",
    )

    assert scorecard["score_version"] == "candidate-score.v1"
    assert scorecard["points"] == 5
    assert scorecard["max_points"] == 5
    assert scorecard["coverage_ratio"] == 1.0
    assert scorecard["usable_for_manager_scoring"] is True
    assert all(row["point"] == 1 for row in scorecard["criteria"].values())


def test_missing_evidence_never_gets_synthetic_points():
    scorecard = build_fundamental_candidate_scorecard(
        {
            "revenue_growth": 0.20,
            "eps_growth": None,
            "free_cash_flow": None,
            "debt_to_equity": 0.3,
            "roic": None,
            "roe": None,
        },
        sector="Technology",
        evidence_status="partial",
    )

    assert scorecard["points"] == 2
    assert scorecard["coverage_ratio"] == 0.4
    assert scorecard["usable_for_manager_scoring"] is False
    assert scorecard["criteria"]["eps_growth"]["available"] is False
    assert scorecard["criteria"]["free_cash_flow"]["point"] == 0


def test_evidence_contract_publishes_scorecard_in_provenance():
    evidence = build_fundamental_evidence(
        {
            "score": 0.82,
            "score_details": {
                "quality_score": 0.8,
                "growth_score": 0.8,
                "valuation_score": 0.7,
                "financial_health_score": 0.9,
                "cash_flow_score": 0.8,
            },
            "key_metrics": {
                "roe": 0.20,
                "roic": 0.15,
                "revenue_growth": 0.15,
                "eps_growth": 0.18,
                "revenue_3y_cagr": 0.14,
                "pe_ratio": 24,
                "debt_to_equity": 0.4,
                "free_cash_flow": 5_000_000,
            },
            "sector": "Technology",
        },
        data_quality_score=0.95,
        style="growth",
    )

    scorecard = evidence["provenance"]["candidate_scorecard"]
    assert scorecard["score_version"] == "candidate-score.v1"
    assert scorecard["points"] == 5
    assert evidence["raw_scores"]["candidate_fundamental_points"] == 5
