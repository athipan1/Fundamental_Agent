import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.analyzer import calculate_quality_score
from app.rule_based_analyzer import _analyze_quality

# Test Data
sample_data_quality = {
    "ROE": 0.25,
    "Debt to Equity Ratio": 20,
    "Profit Margins": 0.30,
    "Operating Cash Flow": 1000000000,
    "EPS": 5.0,
    "Sector": "Technology",
    "Industry": "Software",
    "Market Cap": 1000000000000
}

def test_calculate_quality_score():
    """Test the quality scoring logic."""
    scores = calculate_quality_score(sample_data_quality)
    # Total score should be high for this good data
    assert scores["total"] > 0.6
    assert scores["profitability"] > 0.3
    assert scores["stability"] > 0.15
    assert scores["earnings_quality"] > 0.1

def test_analyze_quality_rule_based():
    """Test the rule-based fallback for quality style."""
    result = _analyze_quality(sample_data_quality)
    assert result["strength"] in ["buy", "strong_buy"]
    assert "ROE > 15%" in result["reasoning"]
    assert "Debt to Equity Ratio < 100" in result["reasoning"]
    assert result["score"] >= 0.8 # 0.3 (base) + 0.35 (roe) + 0.35 (de) = 1.0, but capped at 1.0
