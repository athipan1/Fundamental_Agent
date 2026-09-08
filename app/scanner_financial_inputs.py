"""Explicit Scanner units; no fabricated fiscal history or cash-flow values."""

from datetime import datetime, timezone
import math


def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def _percent(value):
    result = number(value)
    return result / 100.0 if result is not None else None


def _canonical_payload(context):
    metadata = context.get("metadata") or {}
    bundle = context.get("data_bundle") or metadata.get("data_bundle") or {}
    payload = bundle.get("financial_inputs") or {}
    if payload.get("schema_version") != "scanner-financial-inputs.v1":
        return None
    symbol = str(context.get("symbol") or context.get("ticker") or "").upper()
    if payload.get("symbol") != symbol or payload.get("synthetic") is not False:
        return None
    if payload.get("ratio_unit") != "decimal":
        return None
    try:
        observed = datetime.fromisoformat(payload["observed_at"].replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - observed).total_seconds()
        if age < -60 or age > 21600:
            return None
    except (KeyError, TypeError, ValueError):
        return None
    return payload


def prefetched_financial_data(context):
    if not isinstance(context, dict) or not context:
        return {}
    metadata = context.get("metadata") or {}
    raw = context.get("raw_scores") or metadata.get("raw_scores") or {}
    # Scanner raw growth fields are decimal; ROE/ROA/margins are percent.
    # eps_growth and fcf_growth are TOTAL growth, not annualized CAGR.
    values = {
        "ROE": _percent(raw.get("roe")),
        "ROA": _percent(raw.get("roa")),
        "Profit Margins": _percent(raw.get("profit_margins")),
        "Debt to Equity Ratio": number(raw.get("debt_to_equity")),
        "Debt to Equity Unit": "ratio",
        "P/E Ratio": number(raw.get("pe_ratio")),
        "PEG Ratio": number(raw.get("peg_ratio")),
        "P/B Ratio": number(raw.get("pb_ratio")),
        "Free Cash Flow": number(raw.get("free_cash_flow")),
        "Operating Cash Flow": number(raw.get("operating_cash_flow")),
        "Market Cap": number(raw.get("market_cap")),
        "Revenue Growth": number(raw.get("revenue_3y_cagr")),
        "Quarterly Revenue Growth": number(raw.get("qoq_revenue_growth")),
        "Quarterly EPS Growth": number(raw.get("qoq_eps_growth")),
        "Quarterly FCF Growth": number(raw.get("qoq_fcf_growth")),
        "Sector": metadata.get("sector") or context.get("sector"),
        "Data Quality Warning": "scanner_prefetched_data",
    }
    if values["Revenue Growth"] is None:
        values["Revenue Growth"] = _percent(raw.get("revenue_cagr"))
    payload = _canonical_payload(context)
    if payload is not None:
        for key, value in (payload.get("values") or {}).items():
            if value is not None and value != {}:
                values[key] = value
    values["Scanner Input Trace"] = {
        "schema_version": "scanner-input-normalization.v2",
        "synthetic_history_created": False,
        "canonical_history_available": payload is not None,
        "source_observed_at": payload.get("observed_at") if payload else None,
        "growth_unit": "decimal",
        "quality_raw_unit": "percent",
        "quality_output_unit": "decimal",
        "total_growth_not_used_as_cagr": {
            key: raw.get(key) for key in ("eps_growth", "fcf_growth", "fcf_3y_cagr")
        },
        "legacy_cagr_alias_rejected": True,
        "operating_cash_flow_substituted": False,
    }
    return values
