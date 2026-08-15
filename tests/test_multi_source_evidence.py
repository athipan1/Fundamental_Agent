from unittest.mock import patch

from app.evidence_reconciler import reconcile_financial_sources
from app.sec_data_provider import fetch_sec_financial_data


def _company_facts():
    def fact(label, unit, rows):
        return {label: {"units": {unit: rows}}}

    annual_revenue = [
        {
            "end": "2022-12-31",
            "val": 100.0,
            "form": "10-K",
            "fp": "FY",
            "filed": "2023-02-01",
            "accn": "a1",
        },
        {
            "end": "2023-12-31",
            "val": 120.0,
            "form": "10-K",
            "fp": "FY",
            "filed": "2024-02-01",
            "accn": "a2",
        },
        {
            "end": "2024-12-31",
            "val": 150.0,
            "form": "10-K",
            "fp": "FY",
            "filed": "2025-02-01",
            "accn": "a3",
        },
        {
            "end": "2025-03-31",
            "val": 42.0,
            "form": "10-Q",
            "fp": "Q1",
            "filed": "2025-05-01",
            "frame": "CY2025Q1",
            "accn": "q1",
        },
    ]
    annual_ocf = [
        {
            "end": "2024-12-31",
            "val": 30.0,
            "form": "10-K",
            "fp": "FY",
            "filed": "2025-02-01",
            "accn": "a3",
        }
    ]
    annual_capex = [
        {
            "end": "2024-12-31",
            "val": 5.0,
            "form": "10-K",
            "fp": "FY",
            "filed": "2025-02-01",
            "accn": "a3",
        }
    ]
    facts = {}
    facts.update(
        fact(
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "USD",
            annual_revenue,
        )
    )
    facts.update(
        fact(
            "NetCashProvidedByUsedInOperatingActivities",
            "USD",
            annual_ocf,
        )
    )
    facts.update(
        fact(
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "USD",
            annual_capex,
        )
    )
    return {"entityName": "Example Corp", "facts": {"us-gaap": facts}}


@patch("app.sec_data_provider.sec_enabled", return_value=True)
@patch("app.sec_data_provider.resolve_cik", return_value="0000123456")
@patch("app.sec_data_provider._fetch_json", return_value=_company_facts())
def test_sec_provider_builds_filing_history(mock_fetch, mock_cik, mock_enabled):
    result = fetch_sec_financial_data("EXM")

    assert result["Historical Revenue"]["2024-12-31"] == 150.0
    assert result["Quarterly Revenue"]["2025-03-31"] == 42.0
    assert result["Historical Free Cash Flow"]["2024-12-31"] == 25.0
    assert result["SEC Evidence"]["status"] == "success"
    assert result["SEC Evidence"]["cik"] == "0000123456"


def test_reconciler_prefers_sec_for_matching_filing_periods():
    yahoo = {
        "Historical Revenue": {
            "2023-12-31": 118.0,
            "2024-12-31": 149.0,
        }
    }
    sec = {
        "Historical Revenue": {
            "2023-12-31": 120.0,
            "2024-12-31": 150.0,
        },
        "SEC Evidence": {"status": "success", "cik": "0000123456"},
    }

    result = reconcile_financial_sources(yahoo, sec)

    assert result["Historical Revenue"]["2024-12-31"] == 150.0
    reconciliation = result["Source Reconciliation"]
    assert reconciliation["status"] == "multi_source_verified"
    assert reconciliation["divergence_fields"] == []
    assert "sec_edgar_companyfacts" in reconciliation["providers"]


def test_reconciler_flags_material_cross_source_divergence():
    yahoo = {"Historical Revenue": {"2024-12-31": 100.0}}
    sec = {
        "Historical Revenue": {"2024-12-31": 150.0},
        "SEC Evidence": {"status": "success", "cik": "0000123456"},
    }

    result = reconcile_financial_sources(yahoo, sec)

    assert result["Source Reconciliation"]["status"] == "multi_source_divergent"
    assert result["Source Reconciliation"]["divergence_fields"] == [
        "Historical Revenue"
    ]
    assert "cross_source_divergence" in result["Data Quality Warning"]


def test_reconciler_keeps_yahoo_when_sec_is_unavailable():
    yahoo = {"Historical Revenue": {"2024-12-31": 100.0}}
    sec = {"SEC Evidence": {"status": "error", "error": "timeout"}}

    result = reconcile_financial_sources(yahoo, sec)

    assert result["Historical Revenue"]["2024-12-31"] == 100.0
    assert result["Source Reconciliation"]["status"] == "single_source_yahoo"
    assert "sec_source_unavailable" in result["Data Quality Warning"]
