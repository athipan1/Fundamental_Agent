from app.fundamental_engine_v2 import run_fundamental_v2, action_from_score


def test_buy_threshold_is_not_lowered_for_neutral_scores():
    assert action_from_score(0.62, []) == "neutral"
    assert action_from_score(0.71, []) == "neutral"
    assert action_from_score(0.72, []) == "buy"


def test_fundamental_blockers_are_diagnostic_only_for_missing_data():
    # Missing provider metrics are not fabricated to create a buy.
    result = run_fundamental_v2("TEST", {}, "growth")
    trace = result["decision_trace"]
    assert result["strength"] != "buy"
    assert trace["research_only"] is True
    assert trace["research_authorizes_buy"] is False
    assert trace["buy_blocker_codes"]
    assert "FUNDAMENTAL_SCORE_BELOW_BUY_THRESHOLD" in trace["buy_blocker_codes"]
    components = trace["weakest_score_components"]
    assert len(components) == 5
    assert all("existing_weight" in row and "observed_score" in row for row in components)
    assert sum(row["existing_weight"] for row in components) == 1.0
