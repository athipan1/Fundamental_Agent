from __future__ import annotations

import math
import os
from typing import Any, Dict, Iterable, Mapping, Optional

_HISTORY_FIELDS = (
    "Historical Revenue",
    "Historical Net Income",
    "Historical EPS",
    "Historical Operating Cash Flow",
    "Historical Free Cash Flow",
    "Historical FCF",
    "Quarterly Revenue",
    "Quarterly Net Income",
    "Quarterly EPS",
    "Quarterly Operating Cash Flow",
)


def _number(value: Any) -> Optional[float]:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _mapping(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _divergence_tolerance() -> float:
    raw = os.getenv("FUNDAMENTAL_SOURCE_DIVERGENCE_TOLERANCE", "0.20")
    try:
        return max(0.01, min(1.0, float(raw)))
    except (TypeError, ValueError):
        return 0.20


def _relative_difference(left: Any, right: Any) -> Optional[float]:
    left_number = _number(left)
    right_number = _number(right)
    if left_number is None or right_number is None:
        return None
    denominator = max(abs(left_number), abs(right_number), 1e-12)
    return abs(left_number - right_number) / denominator


def _normalized_history(value: Any) -> Dict[str, float]:
    if not isinstance(value, Mapping):
        return {}
    result: Dict[str, float] = {}
    for end, raw in value.items():
        number = _number(raw)
        if number is not None:
            result[str(end)] = number
    return result


def _bounded_history(value: Mapping[str, float], limit: int = 5) -> Dict[str, float]:
    keys = sorted(value)[-limit:]
    return {key: value[key] for key in keys}


def _merge_history(primary: Any, filing: Any) -> Dict[str, float]:
    merged = _normalized_history(primary)
    merged.update(_normalized_history(filing))
    return _bounded_history(merged)


def _latest_common_comparison(
    primary: Any,
    filing: Any,
) -> Optional[Dict[str, Any]]:
    primary_history = _normalized_history(primary)
    filing_history = _normalized_history(filing)
    common = sorted(set(primary_history).intersection(filing_history))
    if not common:
        return None
    end = common[-1]
    difference = _relative_difference(primary_history[end], filing_history[end])
    if difference is None:
        return None
    return {
        "period_end": end,
        "yahoo_value": primary_history[end],
        "sec_value": filing_history[end],
        "relative_difference": round(difference, 6),
    }


def _warning_tokens(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        values: Iterable[Any] = value
    else:
        values = str(value).split(";")
    result: list[str] = []
    for item in values:
        token = str(item).strip()
        if token and token not in result:
            result.append(token)
    return result


def _append_warning(data: Dict[str, Any], warning: str) -> None:
    warnings = _warning_tokens(data.get("Data Quality Warning"))
    if warning not in warnings:
        warnings.append(warning)
    data["Data Quality Warning"] = ";".join(warnings)


def reconcile_financial_sources(
    yahoo_data: Mapping[str, Any],
    sec_data: Mapping[str, Any],
) -> Dict[str, Any]:
    """Merge filing history into market data and audit cross-source agreement.

    Yahoo remains the source for market/valuation fields. SEC filing history is
    authoritative for matching annual/quarterly statement periods. Divergence is
    surfaced as evidence instead of silently choosing whichever source is newer.
    """
    result = dict(yahoo_data)
    sec = dict(sec_data)
    sec_evidence = _mapping(sec.get("SEC Evidence"))
    sec_status = str(sec_evidence.get("status") or "unknown")
    tolerance = _divergence_tolerance()

    providers = ["yfinance_yahoo_quote"]
    comparisons: Dict[str, Dict[str, Any]] = {}
    divergence_fields: list[str] = []
    sec_fields_used: list[str] = []

    if sec_status == "success":
        for field in _HISTORY_FIELDS:
            filing_history = sec.get(field)
            if not _normalized_history(filing_history):
                continue
            comparison = _latest_common_comparison(result.get(field), filing_history)
            if comparison:
                comparisons[field] = comparison
                if comparison["relative_difference"] > tolerance:
                    divergence_fields.append(field)
            result[field] = _merge_history(result.get(field), filing_history)
            sec_fields_used.append(field)

        if sec_fields_used:
            providers.append("sec_edgar_companyfacts")
            reconciliation_status = (
                "multi_source_divergent"
                if divergence_fields
                else "multi_source_verified"
            )
            if divergence_fields:
                _append_warning(result, "cross_source_divergence")
        else:
            reconciliation_status = "single_source_yahoo"
    else:
        reconciliation_status = "single_source_yahoo"
        if sec_status == "error":
            _append_warning(result, "sec_source_unavailable")

    result["SEC Evidence"] = sec_evidence
    result["Source Reconciliation"] = {
        "status": reconciliation_status,
        "providers": providers,
        "sec_status": sec_status,
        "sec_cik": sec_evidence.get("cik"),
        "divergence_tolerance": tolerance,
        "divergence_fields": sorted(divergence_fields),
        "comparisons": comparisons,
        "sec_fields_used": sorted(sec_fields_used),
        "policy": (
            "yahoo_market_fields_plus_sec_filing_history_with_divergence_gate"
        ),
    }
    return result
