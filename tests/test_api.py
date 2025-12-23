import sys
import os
from unittest.mock import patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


@patch('app.main.run_analysis')
def test_analyze_endpoint_growth(mock_run_analysis):
    """Test the /analyze endpoint with the 'growth' style."""
    mock_run_analysis.return_value = {
        "strength": "buy", "score": 0.75, "reasoning": "Strong growth prospects."
    }
    response = client.post("/analyze", json={"ticker": "AAPL", "style": "growth"})
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "action" in data["data"]
    assert data["data"]["action"] in ["buy", "sell", "hold"]
    assert "confidence_score" in data["data"]
    assert "reason" in data["data"]


@patch('app.main.run_analysis')
def test_analyze_endpoint_value(mock_run_analysis):
    """Test the /analyze endpoint with the 'value' style."""
    mock_run_analysis.return_value = {
        "strength": "neutral", "score": 0.5, "reasoning": "Fairly valued."
    }
    response = client.post("/analyze", json={"ticker": "MSFT", "style": "value"})
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "action" in data["data"]
    assert data["data"]["action"] in ["buy", "sell", "hold"]
    assert "confidence_score" in data["data"]
    assert "reason" in data["data"]


@patch('app.main.run_analysis')
def test_analyze_endpoint_dividend(mock_run_analysis):
    """Test the /analyze endpoint with the 'dividend' style."""
    mock_run_analysis.return_value = {
        "strength": "strong_buy", "score": 0.9, "reasoning": "High yield and sustainable."
    }
    response = client.post("/analyze", json={"ticker": "KO", "style": "dividend"})
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "action" in data["data"]
    assert data["data"]["action"] in ["buy", "sell", "hold"]
    assert "confidence_score" in data["data"]
    assert "reason" in data["data"]


@patch('app.main.run_analysis')
def test_analyze_endpoint_invalid_ticker(mock_run_analysis):
    """Test the /analyze endpoint with an invalid ticker that returns None."""
    mock_run_analysis.return_value = None
    response = client.post("/analyze", json={"ticker": "INVALIDTICKER", "style": "growth"})
    assert response.status_code == 404
