import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def test_analyze_endpoint_growth():
    """Test the /analyze endpoint with the 'growth' style."""
    response = client.post("/analyze", json={"ticker": "AAPL", "style": "growth"})
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "action" in data["data"]
    assert data["data"]["action"] in ["buy", "sell", "hold"]
    assert "confidence_score" in data["data"]
    assert "reason" in data["data"]


def test_analyze_endpoint_value():
    """Test the /analyze endpoint with the 'value' style."""
    response = client.post("/analyze", json={"ticker": "MSFT", "style": "value"})
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "action" in data["data"]
    assert data["data"]["action"] in ["buy", "sell", "hold"]
    assert "confidence_score" in data["data"]
    assert "reason" in data["data"]


def test_analyze_endpoint_dividend():
    """Test the /analyze endpoint with the 'dividend' style."""
    response = client.post("/analyze", json={"ticker": "KO", "style": "dividend"})
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "action" in data["data"]
    assert data["data"]["action"] in ["buy", "sell", "hold"]
    assert "confidence_score" in data["data"]
    assert "reason" in data["data"]


def test_analyze_endpoint_invalid_ticker():
    """Test the /analyze endpoint with an invalid ticker."""
    response = client.post("/analyze", json={"ticker": "INVALIDTICKER", "style": "growth"})
    # yfinance might still return some data, so we check for a valid score or a 404
    if response.status_code == 200:
        assert response.json()["data"]["confidence_score"] == 0.0
    else:
        assert response.status_code == 404
