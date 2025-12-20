from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_analyze_endpoint_growth():
    """Test the /analyze endpoint with the 'growth' style."""
    response = client.post("/analyze", json={"ticker": "AAPL", "style": "growth"})
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert "recommendation" in data
    assert "full_report" in data
    assert "growth" in data["full_report"]["score_details"]


def test_analyze_endpoint_value():
    """Test the /analyze endpoint with the 'value' style."""
    response = client.post("/analyze", json={"ticker": "MSFT", "style": "value"})
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "MSFT"
    assert "recommendation" in data
    assert "full_report" in data
    assert "valuation" in data["full_report"]["score_details"]


def test_analyze_endpoint_dividend():
    """Test the /analyze endpoint with the 'dividend' style."""
    response = client.post("/analyze", json={"ticker": "KO", "style": "dividend"})
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "KO"
    assert "recommendation" in data
    assert "full_report" in data
    assert "yield" in data["full_report"]["score_details"]


def test_analyze_endpoint_invalid_ticker():
    """Test the /analyze endpoint with an invalid ticker."""
    response = client.post("/analyze", json={"ticker": "INVALIDTICKER", "style": "growth"})
    # yfinance might still return some data, so we check for a valid score or a 404
    if response.status_code == 200:
        assert response.json()["confidence_score"] == 0.0
    else:
        assert response.status_code == 404
