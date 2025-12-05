import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from unittest.mock import patch  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402


client = TestClient(app)


def test_analyze_ticker_success():
    mock_analysis = {
        "company_snapshot": {"name": "Apple Inc."},
        "key_metrics": {"pe_ratio": 25.0}
    }
    with patch('main.run_analysis', return_value=mock_analysis) as mock_run_analysis:
        response = client.get("/analyze/AAPL")
        assert response.status_code == 200
        assert response.json() == mock_analysis
        mock_run_analysis.assert_called_once_with("AAPL")


def test_analyze_ticker_not_found():
    with patch('main.run_analysis', return_value=None) as mock_run_analysis:
        response = client.get("/analyze/INVALIDTICKER")
        assert response.status_code == 404
        assert response.json() == {"detail": "Ticker not found or analysis failed."}
        mock_run_analysis.assert_called_once_with("INVALIDTICKER")
