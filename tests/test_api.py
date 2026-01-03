import sys
import os
from unittest.mock import patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@patch('app.main.run_analysis')
def test_analyze_endpoint_success_growth(mock_run_analysis):
    """Test a successful analysis for the 'growth' style."""
    mock_run_analysis.return_value = {
        "strength": "buy",
        "score": 0.75,
        "reasoning": "Strong growth prospects."
    }
    response = client.post(
        "/analyze",
        json={"ticker": "AAPL", "style": "growth"},
        headers={"X-Correlation-ID": "test-growth-123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "analysis" in data
    assert data["analysis"]["action"] == "buy"
    assert data["analysis"]["confidence"] == 0.75
    assert data["analysis"]["reason"] == "Strong growth prospects."
    assert data["analysis"]["source"] == "fundamental_agent"
    mock_run_analysis.assert_called_with("AAPL", "growth", correlation_id="test-growth-123")


@patch('app.main.run_analysis')
def test_analyze_endpoint_success_value(mock_run_analysis):
    """Test a successful analysis for the 'value' style."""
    mock_run_analysis.return_value = {
        "strength": "neutral",
        "score": 0.5,
        "reasoning": "Fairly valued."
    }
    response = client.post("/analyze", json={"ticker": "MSFT", "style": "value"})
    assert response.status_code == 200
    data = response.json()
    assert "analysis" in data
    assert data["analysis"]["action"] == "hold"
    assert data["analysis"]["confidence"] == 0.5
    assert data["analysis"]["source"] == "fundamental_agent"


@patch('app.main.run_analysis')
def test_analyze_endpoint_ticker_not_found(mock_run_analysis):
    """Test the response for a ticker that is not found."""
    mock_run_analysis.return_value = {"error": "ticker_not_found"}
    response = client.post("/analyze", json={"ticker": "INVALIDTICKER"})
    assert response.status_code == 200
    data = response.json()
    assert "analysis" in data
    assert data["analysis"]["action"] == "hold"
    assert data["analysis"]["confidence"] == 0.0
    assert data["analysis"]["reason"] == "ticker_not_found"
    assert data["analysis"]["source"] == "fundamental_agent"


@patch('app.main.run_analysis')
def test_analyze_endpoint_insufficient_data(mock_run_analysis):
    """Test the response when there is not enough data for analysis."""
    mock_run_analysis.return_value = {"error": "data_not_enough"}
    response = client.post("/analyze", json={"ticker": "NODATA"})
    assert response.status_code == 200
    data = response.json()
    assert "analysis" in data
    assert data["analysis"]["reason"] == "data_not_enough"
    assert data["analysis"]["action"] == "hold"


@patch('app.main.run_analysis')
def test_analyze_endpoint_model_error(mock_run_analysis):
    """Test the response when the analysis model fails."""
    mock_run_analysis.return_value = {"error": "model_error"}
    response = client.post("/analyze", json={"ticker": "FAILMODEL"})
    assert response.status_code == 200
    data = response.json()
    assert "analysis" in data
    assert data["analysis"]["reason"] == "model_error"
    assert data["analysis"]["action"] == "hold"
