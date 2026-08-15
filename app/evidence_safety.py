from __future__ import annotations

from typing import Any, Dict, Mapping

EVIDENCE_CONFLICT_CONFIDENCE_CAP = 0.30


def _mapping(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _normalized_flags(value: Any) -> list[str]:
    flags: list[str] = []
    for raw in value or []:
        for token in str(raw).split(";"):
            normalized = token.strip()
            if normalized and normalized not in flags:
                flags.append(normalized)
    return flags


def apply_reconciliation_safety(
    analysis_result: Mapping[str, Any],
    financial_data: Mapping[str, Any],
) -> Dict[str, Any]:
    """Fail closed to HOLD/review when independent sources materially disagree."""
    result = dict(analysis_result or {})
    reconciliation = _mapping(financial_data.get("Source Reconciliation"))
    if reconciliation.get("status") != "multi_source_divergent":
        return result

    divergence_fields = [
        str(field) for field in reconciliation.get("divergence_fields") or []
    ]
    flags = _normalized_flags(result.get("risk_flags"))
    for flag in ("cross_source_divergence", "evidence_conflict_review_required"):
        if flag not in flags:
            flags.append(flag)
    result["risk_flags"] = flags

    strength = str(result.get("strength") or "neutral").lower()
    if strength in {"buy", "strong_buy"}:
        result["strength"] = "neutral"

    try:
        raw_score = float(result.get("score") or 0.0)
    except (TypeError, ValueError):
        raw_score = 0.0
    result["score"] = min(raw_score, EVIDENCE_CONFLICT_CONFIDENCE_CAP)

    field_text = ", ".join(divergence_fields) if divergence_fields else "unknown"
    note = (
        "Cross-source financial evidence conflict detected for "
        f"{field_text}; Manager review is required before trading."
    )
    reasoning = str(result.get("reasoning") or "").strip()
    result["reasoning"] = f"{reasoning} {note}".strip()

    source = str(result.get("analysis_source") or result.get("source") or "fundamental")
    if not source.endswith("_evidence_conflict_gate"):
        source = f"{source}_evidence_conflict_gate"
    result["analysis_source"] = source
    result["manager_decision_required"] = True
    result["evidence_conflict_review_required"] = True
    return result
