from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Optional

CANDIDATE_SCORE_VERSION = "candidate-score.v1"
FUNDAMENTAL_MAX_POINTS = 5


def _finite(value: Any) -> Optional[float]:
    try:
        if value is None or value == "" or isinstance(value, bool):
            return None
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _first(*values: Any) -> Optional[float]:
    for value in values:
        number = _finite(value)
        if number is not None:
            return number
    return None


def _criterion(*, observed: Optional[float], passed: bool, threshold: str, source: str) -> Dict[str, Any]:
    available = observed is not None
    return {
        "available": available,
        "passed": bool(available and passed),
        "point": 1 if available and passed else 0,
        "observed": observed,
        "threshold": threshold,
        "source": source,
    }


def build_fundamental_candidate_scorecard(
    metrics: Mapping[str, Any],
    *,
    sector: Optional[str] = None,
    evidence_status: Optional[str] = None,
) -> Dict[str, Any]:
    """Project explainable 0-5 fundamental points from existing evidence.

    Missing values never receive a point. This projection is advisory only and
    does not create BUY authority; Manager_Agent owns the final candidate score.
    """

    metrics = dict(metrics or {})
    revenue_growth = _first(metrics.get("revenue_growth"), metrics.get("revenue_3y_cagr"))
    eps_growth = _first(metrics.get("eps_growth"), metrics.get("eps_3y_cagr"))
    free_cash_flow = _finite(metrics.get("free_cash_flow"))
    debt_to_equity = _finite(metrics.get("debt_to_equity"))
    roic = _finite(metrics.get("roic"))
    roe = _finite(metrics.get("roe"))
    financial_health_score = _finite(metrics.get("financial_health_score"))

    normalized_sector = str(sector or metrics.get("sector") or "").strip().lower()
    if normalized_sector in {"real estate", "utilities"}:
        debt_limit = 2.5
    elif normalized_sector == "financial services":
        debt_limit = None
    else:
        debt_limit = 1.0

    if debt_limit is None:
        debt_observed = financial_health_score
        debt_passed = debt_observed is not None and debt_observed >= 0.60
        debt_threshold = "financial_health_score >= 0.60 (sector-aware substitute)"
        debt_source = "financial_health_score"
    else:
        debt_observed = debt_to_equity
        debt_passed = debt_observed is not None and 0 <= debt_observed <= debt_limit
        debt_threshold = f"0 <= debt_to_equity <= {debt_limit}"
        debt_source = "debt_to_equity"

    efficiency_observed = roic if roic is not None else roe
    efficiency_passed = (
        (roic is not None and roic >= 0.10)
        or (roic is None and roe is not None and roe >= 0.15)
    )
    efficiency_threshold = "ROIC >= 0.10; fallback ROE >= 0.15"
    efficiency_source = "roic" if roic is not None else "roe"

    criteria = {
        "revenue_growth": _criterion(
            observed=revenue_growth,
            passed=revenue_growth is not None and revenue_growth >= 0.10,
            threshold="revenue_growth or revenue_3y_cagr >= 0.10",
            source="revenue_growth|revenue_3y_cagr",
        ),
        "eps_growth": _criterion(
            observed=eps_growth,
            passed=eps_growth is not None and eps_growth >= 0.10,
            threshold="eps_growth or eps_3y_cagr >= 0.10",
            source="eps_growth|eps_3y_cagr",
        ),
        "free_cash_flow": _criterion(
            observed=free_cash_flow,
            passed=free_cash_flow is not None and free_cash_flow > 0,
            threshold="free_cash_flow > 0",
            source="free_cash_flow",
        ),
        "debt_quality": _criterion(
            observed=debt_observed,
            passed=debt_passed,
            threshold=debt_threshold,
            source=debt_source,
        ),
        "capital_efficiency": _criterion(
            observed=efficiency_observed,
            passed=efficiency_passed,
            threshold=efficiency_threshold,
            source=efficiency_source,
        ),
    }

    points = sum(int(item["point"]) for item in criteria.values())
    available = sum(1 for item in criteria.values() if item["available"])
    evidence_complete = available == FUNDAMENTAL_MAX_POINTS
    usable = evidence_status not in {"insufficient", "unavailable"}

    return {
        "score_version": CANDIDATE_SCORE_VERSION,
        "scope": "fundamental",
        "points": points,
        "max_points": FUNDAMENTAL_MAX_POINTS,
        "coverage_ratio": round(available / FUNDAMENTAL_MAX_POINTS, 4),
        "evidence_complete": evidence_complete,
        "usable_for_manager_scoring": bool(usable and evidence_complete),
        "criteria": criteria,
        "authority": "advisory_only",
        "manager_decision_required": True,
    }
