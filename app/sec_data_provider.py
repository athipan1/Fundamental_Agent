from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_COMPANY_FACTS_URL = (
    "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
)
DEFAULT_SEC_USER_AGENT = (
    "Fundamental_Agent/1.2 athipan1@users.noreply.github.com"
)
DEFAULT_TIMEOUT_SECONDS = 6.0
DEFAULT_MIN_REQUEST_INTERVAL_SECONDS = 0.12

_ANNUAL_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}
_QUARTERLY_FORMS = {"10-Q", "10-Q/A"}
_QUARTER_FRAME = re.compile(r"^CY\d{4}Q[1-4]$")

_CONCEPTS = {
    "revenue": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ),
    "net_income": ("NetIncomeLoss",),
    "eps": ("EarningsPerShareDiluted", "EarningsPerShareBasic"),
    "operating_cash_flow": (
        "NetCashProvidedByUsedInOperatingActivities",
    ),
    "capital_expenditure": (
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsForAdditionsToPropertyPlantAndEquipment",
    ),
}

_UNIT_PREFERENCES = {
    "revenue": ("USD",),
    "net_income": ("USD",),
    "eps": ("USD/shares", "USD / shares"),
    "operating_cash_flow": ("USD",),
    "capital_expenditure": ("USD",),
}

_ticker_cache: Optional[Dict[str, str]] = None
_request_lock = threading.Lock()
_last_request_monotonic = 0.0


def sec_enabled() -> bool:
    raw = os.getenv("FUNDAMENTAL_SEC_ENABLED", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _timeout_seconds() -> float:
    raw = os.getenv("SEC_REQUEST_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
    try:
        return max(1.0, min(30.0, float(raw)))
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT_SECONDS


def _min_request_interval_seconds() -> float:
    raw = os.getenv(
        "SEC_MIN_REQUEST_INTERVAL_SECONDS",
        str(DEFAULT_MIN_REQUEST_INTERVAL_SECONDS),
    )
    try:
        return max(0.10, min(2.0, float(raw)))
    except (TypeError, ValueError):
        return DEFAULT_MIN_REQUEST_INTERVAL_SECONDS


def _declared_user_agent() -> str:
    return os.getenv("SEC_USER_AGENT", DEFAULT_SEC_USER_AGENT).strip() or (
        DEFAULT_SEC_USER_AGENT
    )


def _throttle() -> None:
    global _last_request_monotonic
    with _request_lock:
        now = time.monotonic()
        wait = _min_request_interval_seconds() - (now - _last_request_monotonic)
        if wait > 0:
            time.sleep(wait)
        _last_request_monotonic = time.monotonic()


def _fetch_json(url: str) -> Dict[str, Any]:
    _throttle()
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": _declared_user_agent(),
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        },
    )
    with urllib.request.urlopen(request, timeout=_timeout_seconds()) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return dict(payload) if isinstance(payload, Mapping) else {}


def _normalized_ticker(ticker: str) -> str:
    return ticker.upper().strip().replace(".", "-").replace("/", "-")


def _ticker_map() -> Dict[str, str]:
    global _ticker_cache
    if _ticker_cache is not None:
        return _ticker_cache

    payload = _fetch_json(SEC_COMPANY_TICKERS_URL)
    result: Dict[str, str] = {}
    for row in payload.values():
        if not isinstance(row, Mapping):
            continue
        ticker = _normalized_ticker(str(row.get("ticker") or ""))
        cik = row.get("cik_str")
        if not ticker or cik in (None, ""):
            continue
        try:
            result[ticker] = f"{int(cik):010d}"
        except (TypeError, ValueError):
            continue
    _ticker_cache = result
    return result


def resolve_cik(ticker: str) -> Optional[str]:
    return _ticker_map().get(_normalized_ticker(ticker))


def _taxonomy(company_facts: Mapping[str, Any]) -> Mapping[str, Any]:
    facts = company_facts.get("facts")
    if not isinstance(facts, Mapping):
        return {}
    us_gaap = facts.get("us-gaap")
    return us_gaap if isinstance(us_gaap, Mapping) else {}


def _unit_rows(
    company_facts: Mapping[str, Any],
    concepts: Iterable[str],
    unit_preferences: Iterable[str],
) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    taxonomy = _taxonomy(company_facts)
    for concept in concepts:
        definition = taxonomy.get(concept)
        if not isinstance(definition, Mapping):
            continue
        units = definition.get("units")
        if not isinstance(units, Mapping):
            continue
        for unit in unit_preferences:
            rows = units.get(unit)
            if isinstance(rows, list) and rows:
                return concept, [dict(row) for row in rows if isinstance(row, Mapping)]
        for rows in units.values():
            if isinstance(rows, list) and rows:
                return concept, [dict(row) for row in rows if isinstance(row, Mapping)]
    return None, []


def _latest_by_end(rows: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    selected: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        end = str(row.get("end") or "")
        if not end or row.get("val") is None:
            continue
        candidate = dict(row)
        previous = selected.get(end)
        if previous is None:
            selected[end] = candidate
            continue
        if str(candidate.get("filed") or "") >= str(previous.get("filed") or ""):
            selected[end] = candidate
    return [selected[key] for key in sorted(selected)]


def _annual_rows(rows: Iterable[Mapping[str, Any]], limit: int = 4) -> List[Dict[str, Any]]:
    annual = [
        row
        for row in rows
        if str(row.get("form") or "") in _ANNUAL_FORMS
        and str(row.get("fp") or "") == "FY"
    ]
    return _latest_by_end(annual)[-limit:]


def _quarterly_rows(
    rows: Iterable[Mapping[str, Any]],
    limit: int = 5,
) -> List[Dict[str, Any]]:
    quarterly = [
        row
        for row in rows
        if str(row.get("form") or "") in _QUARTERLY_FORMS
        and _QUARTER_FRAME.match(str(row.get("frame") or ""))
    ]
    return _latest_by_end(quarterly)[-limit:]


def _history(rows: Iterable[Mapping[str, Any]]) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for row in rows:
        end = str(row.get("end") or "")
        try:
            value = float(row.get("val"))
        except (TypeError, ValueError):
            continue
        if end:
            result[end] = value
    return result


def _fact_provenance(
    concept: Optional[str],
    rows: Iterable[Mapping[str, Any]],
) -> Dict[str, Any]:
    rows = list(rows)
    latest = rows[-1] if rows else {}
    return {
        "concept": concept,
        "latest_end": latest.get("end"),
        "latest_filed": latest.get("filed"),
        "latest_form": latest.get("form"),
        "latest_accession": latest.get("accn"),
        "period_count": len(rows),
    }


def _derive_fcf(
    operating_cash_flow: Mapping[str, float],
    capital_expenditure: Mapping[str, float],
) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for end, ocf in operating_cash_flow.items():
        capex = capital_expenditure.get(end)
        if capex is None:
            continue
        result[end] = float(ocf) - abs(float(capex))
    return result


def _evidence_status(
    cik: Optional[str],
    status: str,
    *,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "provider": "sec_edgar_companyfacts",
        "status": status,
        "cik": cik,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "error": error,
    }


def fetch_sec_financial_data(ticker: str) -> Dict[str, Any]:
    """Fetch filing-derived financial evidence from SEC EDGAR.

    The provider is best-effort. It never raises into the trading path; callers
    receive status metadata and can retain their primary market-data source.
    """
    if not sec_enabled():
        return {"SEC Evidence": _evidence_status(None, "disabled")}

    cik: Optional[str] = None
    try:
        cik = resolve_cik(ticker)
        if not cik:
            return {"SEC Evidence": _evidence_status(None, "not_applicable")}

        company_facts = _fetch_json(SEC_COMPANY_FACTS_URL.format(cik=cik))
        result: Dict[str, Any] = {}
        fact_metadata: Dict[str, Any] = {}
        annual_histories: Dict[str, Dict[str, float]] = {}

        field_map = {
            "revenue": ("Historical Revenue", "Quarterly Revenue"),
            "net_income": ("Historical Net Income", "Quarterly Net Income"),
            "eps": ("Historical EPS", "Quarterly EPS"),
            "operating_cash_flow": (
                "Historical Operating Cash Flow",
                "Quarterly Operating Cash Flow",
            ),
            "capital_expenditure": (
                "Historical Capital Expenditure",
                "Quarterly Capital Expenditure",
            ),
        }

        for key, (annual_field, quarterly_field) in field_map.items():
            concept, rows = _unit_rows(
                company_facts,
                _CONCEPTS[key],
                _UNIT_PREFERENCES[key],
            )
            annual = _annual_rows(rows)
            quarterly = _quarterly_rows(rows)
            annual_history = _history(annual)
            quarterly_history = _history(quarterly)
            if annual_history:
                result[annual_field] = annual_history
                annual_histories[key] = annual_history
            if quarterly_history:
                result[quarterly_field] = quarterly_history
            fact_metadata[key] = _fact_provenance(concept, annual or quarterly)

        fcf_history = _derive_fcf(
            annual_histories.get("operating_cash_flow", {}),
            annual_histories.get("capital_expenditure", {}),
        )
        if fcf_history:
            result["Historical Free Cash Flow"] = fcf_history
            result["Historical FCF"] = dict(fcf_history)

        evidence = _evidence_status(cik, "success")
        evidence.update(
            {
                "entity_name": company_facts.get("entityName"),
                "facts": fact_metadata,
                "available_fields": sorted(result.keys()),
            }
        )
        result["SEC Evidence"] = evidence
        return result
    except Exception as exc:
        return {
            "SEC Evidence": _evidence_status(
                cik,
                "error",
                error=f"{type(exc).__name__}: {exc}",
            )
        }
