from app.evidence_safety import apply_reconciliation_safety


def test_evidence_conflict_blocks_buy_and_caps_confidence():
    analysis = {
        "strength": "buy",
        "score": 0.82,
        "reasoning": "Strong fundamentals.",
        "risk_flags": [],
        "analysis_source": "fundamental_engine_v2",
    }
    financial_data = {
        "Source Reconciliation": {
            "status": "multi_source_divergent",
            "divergence_fields": ["Historical Revenue"],
        }
    }

    result = apply_reconciliation_safety(analysis, financial_data)

    assert result["strength"] == "neutral"
    assert result["score"] == 0.30
    assert "cross_source_divergence" in result["risk_flags"]
    assert "evidence_conflict_review_required" in result["risk_flags"]
    assert result["evidence_conflict_review_required"] is True
    assert "Manager review is required" in result["reasoning"]


def test_evidence_conflict_does_not_promote_sell_to_hold():
    analysis = {"strength": "sell", "score": 0.20, "risk_flags": ["negative_eps"]}
    financial_data = {
        "Source Reconciliation": {
            "status": "multi_source_divergent",
            "divergence_fields": ["Historical EPS"],
        }
    }

    result = apply_reconciliation_safety(analysis, financial_data)

    assert result["strength"] == "sell"
    assert result["score"] == 0.20


def test_verified_multi_source_data_keeps_original_decision():
    analysis = {"strength": "buy", "score": 0.78, "risk_flags": []}
    financial_data = {
        "Source Reconciliation": {"status": "multi_source_verified"}
    }

    result = apply_reconciliation_safety(analysis, financial_data)

    assert result == analysis
