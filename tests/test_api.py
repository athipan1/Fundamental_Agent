import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from unittest.mock import patch  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402


client = TestClient(app)


def test_analyze_ticker_success():
    """Test successful analysis and response transformation."""
    # 1. Mock the output of the *internal* run_analysis function
    mock_run_analysis_result = {
        "strength": "พื้นฐานแข็งแกร่ง",
        "reasoning": "This is a test summary.",
        "score": 0.85
    }

    # 2. Define the *expected* final JSON output from the API endpoint
    expected_orchestrator_response = {
        "ticker": "AAPL",
        "recommendation": "พื้นฐานแข็งแกร่ง",
        "confidence_score": 0.85,
        "analysis_summary": "This is a test summary.",
        "full_report": "This is a test summary."
    }

    with patch('main.run_analysis', return_value=mock_run_analysis_result) as mock_run_analysis:
        response = client.post("/analyze", json={"ticker": "AAPL"})

        # 3. Assertions
        assert response.status_code == 200
        assert response.json() == expected_orchestrator_response
        mock_run_analysis.assert_called_once_with("AAPL")


def test_analyze_ticker_not_found():
    """Test the case where the ticker is not found or analysis fails."""
    with patch('main.run_analysis', return_value=None) as mock_run_analysis:
        response = client.post("/analyze", json={"ticker": "INVALIDTICKER"})
        assert response.status_code == 404
        assert response.json() == {"detail": "Ticker not found or analysis failed."}
        mock_run_analysis.assert_called_once_with("INVALIDTICKER")


def test_analyze_ticker_invalid_request():
    """Test request with invalid JSON body."""
    response = client.post("/analyze", json={"company": "AAPL"})
    # FastAPI should return a 422 Unprocessable Entity for Pydantic validation errors
    assert response.status_code == 422
