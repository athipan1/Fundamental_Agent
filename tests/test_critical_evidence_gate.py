from app.fundamental_evidence import build_fundamental_evidence


def _complete_analysis() -> dict:
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
        "sector": "Technology",
        "risk_flags": [],
        "key_metrics": {
            "roe": 0.18,
            "roa": 0.08,
            "roic": 0.14,
            "profit_margins": 0.21,
            "operating_margin": 0.24,
            "gross_margin": 0.48,
            "fcf_margin": 0.17,
            "cash_conversion": 0.91,
            "interest_coverage": 12.0,
            "eps": 7.1,
            "revenue_growth": 0.11,
            "eps_growth": 0.13,
            "fcf_growth": 0.12,
            "revenue_3y_cagr": 0.10,
            "eps_3y_cagr": 0.12,
            "fcf_3y_cagr": 0.11,
            "ocf_3y_cagr": 0.10,
            "qoq_revenue_growth": 0.03,
            "qoq_eps_growth": 0.04,
            "qoq_fcf_growth": 0.03,
            "qoq_ocf_growth": 0.02,
            "pe_ratio": 22.0,
            "forward_pe": 20.0,
            "peg_ratio": 1.5,
            "pb_ratio": 5.0,
            "ev_to_ebitda": 14.0,
            "price_to_sales": 6.0,
            "price_to_fcf": 24.0,
            "fcf_yield": 0.041,
            "debt_to_equity": 0.45,
            "operating_cash_flow": 12_000_000,
            "free_cash_flow": 9_000_000,
            "net_income": 8_000_000,
            "market_cap": 250_000_000_000,
            "net_cash": 15_000_000,
            "dividend_yield": 0.008,
            "dividend_rate": 1.0,
            "payout_ratio": 0.22,
        },
    }


def test_complete_evidence_remains_complete():
    evidence = build_fundamental_evidence(
        _complete_analysis(),
        data_quality_score=0.95,
        style="growth",
    )

    assert evidence["evidence_status"] == "complete"
    assert evidence["missing_critical_metrics"] == []


def test_one_missing_critical_metric_fails_closed_even_with_high_completeness():
    analysis = _complete_analysis()
    analysis["key_metrics"].pop("pe_ratio")

    evidence = build_fundamental_evidence(
        analysis,
        data_quality_score=0.95,
        style="growth",
    )

    assert evidence["evidence_completeness_score"] >= 0.80
    assert evidence["missing_critical_metrics"] == ["pe_ratio"]
    assert evidence["evidence_status"] == "insufficient"
    assert any(
        reason.startswith("missing_critical_metrics:pe_ratio")
        for reason in evidence["evidence_reasons"]
    )


def test_weak_fundamentals_with_complete_data_are_not_mislabeled_as_data_failure():
    analysis = _complete_analysis()
    analysis["score"] = 0.20
    analysis["score_details"].update(
        {
            "quality_score": 0.20,
            "growth_score": 0.15,
            "valuation_score": 0.25,
            "financial_health_score": 0.30,
            "cash_flow_score": 0.20,
        }
    )

    evidence = build_fundamental_evidence(
        analysis,
        data_quality_score=0.95,
        style="growth",
    )

    assert evidence["evidence_status"] == "complete"
    assert evidence["missing_critical_metrics"] == []
    assert evidence["raw_scores"]["fundamental_score"] == 0.20
