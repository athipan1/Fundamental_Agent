from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional


FUNDAMENTAL_EVIDENCE_VERSION = "fundamental-evidence-v1"
BUCKET_DECISION_AUTHORITY = "manager"

_SCORE_FIELDS = (
    "quality_score",
    "growth_score",
    "valuation_score",
    "financial_health_score",
    "cash_flow_score",
)

_METRIC_ALIASES = {
    "roe": ("roe",),
    "roa": ("roa",),
    "roic": ("roic",),
    "profit_margins": ("profit_margins", "profit_margin"),
    "operating_margin": ("operating_margin",),
    "gross_margin": ("gross_margin",),
    "fcf_margin": ("fcf_margin",),
    "cash_conversion": ("cash_conversion",),
    "interest_coverage": ("interest_coverage",),
    "eps": ("eps",),
    "revenue_growth": ("revenue_growth",),
    "eps_growth": ("eps_growth", "earnings_growth"),
    "fcf_growth": ("fcf_growth",),
    "revenue_3y_cagr": ("revenue_3y_cagr",),
    "eps_3y_cagr": ("eps_3y_cagr",),
    "fcf_3y_cagr": ("fcf_3y_cagr",),
    "ocf_3y_cagr": ("ocf_3y_cagr",),
    "qoq_revenue_growth": (
        "qoq_revenue_growth",
        "quarterly_revenue_growth",
    ),
    "qoq_eps_growth": (
        "qoq_eps_growth",
        "quarterly_eps_growth",
    ),
    "qoq_fcf_growth": (
        "qoq_fcf_growth",
        "quarterly_fcf_growth",
    ),
    "qoq_ocf_growth": ("qoq_ocf_growth",),
    "pe_ratio": ("pe_ratio",),
    "forward_pe": ("forward_pe",),
    "peg_ratio": ("peg_ratio",),
    "pb_ratio": ("pb_ratio",),
    "ev_to_ebitda": ("ev_to_ebitda",),
    "price_to_sales": ("price_to_sales",),
    "price_to_fcf": ("price_to_fcf",),
    "fcf_yield": ("fcf_yield",),
    "debt_to_equity": ("debt_to_equity",),
    "operating_cash_flow": ("operating_cash_flow",),
    "free_cash_flow": ("free_cash_flow",),
    "net_income": ("net_income",),
    "market_cap": ("market_cap",),
    "net_cash": ("net_cash",),
    "dividend_yield": ("dividend_yield",),
    "dividend_rate": ("dividend_rate",),
    "payout_ratio": ("payout_ratio",),
}

_CRITICAL_FIELDS = (
    "quality_score",
    "growth_score",
    "valuation_score",
    "financial_health_score",
    "cash_flow_score",
    "pe_ratio",
    "debt_to_equity",
    "free_cash_flow",
    "revenue_3y_cagr",
)


def _mapping(value: Any) -> Dict[str, Any]:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return dict(value) if isinstance(value, Mapping) else {}


def _float_or_none(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _score01(value: Any) -> Optional[float]:
    number = _float_or_none(value)
    if number is None:
        return None
    if abs(number) > 1.0:
        number = number / 100.0
    return round(max(0.0, min(1.0, number)), 4)


def _first(mapping: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None and value != "":
            return value
    return None


def _normalize_dividend_yield(value: Any) -> Optional[float]:
    number = _float_or_none(value)
    if number is None:
        return None
    if abs(number) > 1.0:
        number = number / 100.0
    return round(max(0.0, number), 6)


def _normalize_debt_to_equity(value: Any) -> Optional[float]:
    number = _float_or_none(value)
    if number is None:
        return None
    if number > 10.0:
        number = number / 100.0
    return round(number, 6)


def _metric_value(name: str, value: Any) -> Any:
    if name == "dividend_yield":
        return _normalize_dividend_yield(value)
    if name == "debt_to_equity":
        return _normalize_debt_to_equity(value)
    number = _float_or_none(value)
    return round(number, 6) if number is not None else value


def _evidence_status(
    completeness: float,
    missing_critical: list[str],
) -> str:
    # Critical evidence gaps are a data-availability problem, not a weaker
    # fundamental opinion. Fail closed so Manager routes the candidate to
    # REVIEW instead of treating the payload as usable partial evidence.
    if missing_critical:
        return "insufficient"
    if completeness >= 0.80:
        return "complete"
    if completeness >= 0.45:
        return "partial"
    return "insufficient"


def build_fundamental_evidence(
    analysis_result: Mapping[str, Any],
    *,
    data_quality_score: float,
    style: str,
) -> Dict[str, Any]:
    """Create versioned financial evidence for Scanner and Manager.

    Fundamental_Agent publishes normalized evidence only. It never assigns a
    strategy bucket; Manager remains the final decision authority.
    """
    analysis_result = _mapping(analysis_result)
    score_details = _mapping(analysis_result.get("score_details"))
    key_metrics = _mapping(analysis_result.get("key_metrics"))

    raw_scores: Dict[str, Any] = {}
    for field in _SCORE_FIELDS:
        normalized = _score01(score_details.get(field))
        if normalized is not None:
            raw_scores[field] = normalized

    score_value = analysis_result.get("score")
    if score_value is None:
        score_value = analysis_result.get("confidence_score")
    fundamental_score = _score01(score_value)
    if fundamental_score is not None:
        raw_scores["fundamental_score"] = fundamental_score

    metrics: Dict[str, Any] = {}
    for field, aliases in _METRIC_ALIASES.items():
        raw_value = _first(key_metrics, aliases)
        normalized = _metric_value(field, raw_value)
        if normalized is not None:
            metrics[field] = normalized
            raw_scores[field] = normalized

    sector = analysis_result.get("sector")
    if sector:
        metrics["sector"] = str(sector)

    available_fields = sorted(raw_scores.keys())
    expected_fields = sorted(
        set(_SCORE_FIELDS)
        | set(_METRIC_ALIASES)
        | {"fundamental_score"}
    )
    missing_fields = sorted(
        field for field in expected_fields if field not in raw_scores
    )
    missing_critical = sorted(
        field for field in _CRITICAL_FIELDS if field not in raw_scores
    )
    completeness = round(
        len(available_fields) / max(1, len(expected_fields)),
        4,
    )
    status = _evidence_status(completeness, missing_critical)

    reasons: list[str] = [
        f"evidence_status:{status}",
        f"available_fields:{len(available_fields)}",
        f"data_quality_score:{round(float(data_quality_score), 4)}",
    ]
    if missing_critical:
        reasons.append(
            "missing_critical_metrics:" + ",".join(missing_critical)
        )
    risk_flags = [
        str(flag) for flag in analysis_result.get("risk_flags") or []
    ]
    if risk_flags:
        reasons.append("risk_flags:" + ",".join(risk_flags))

    source = str(
        analysis_result.get("analysis_source")
        or analysis_result.get("source")
        or "fundamental_agent"
    )
    provenance = {
        "analysis_source": source,
        "style": style,
        "data_quality_score": round(float(data_quality_score), 4),
        "source_fields": available_fields,
        "synthetic_or_prefetched": (
            "prefetch" in source or "synthetic" in source
        ),
    }

    return {
        "evidence_version": FUNDAMENTAL_EVIDENCE_VERSION,
        "evidence_status": status,
        "evidence_completeness_score": completeness,
        "raw_scores": raw_scores,
        "metrics": metrics,
        "available_fields": available_fields,
        "missing_fields": missing_fields,
        "missing_critical_metrics": missing_critical,
        "evidence_reasons": reasons,
        "risk_flags": risk_flags,
        "provenance": provenance,
        "strategy_bucket_hint": None,
        "bucket_decision_authority": BUCKET_DECISION_AUTHORITY,
        "manager_decision_required": True,
    }
