from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Literal, Dict, Optional, Any, List
from .fundamental_agent import run_analysis
from .fundamental_engine_v2 import run_fundamental_v2, action_from_score, SEVERE_FLAGS
from .scanner_financial_inputs import prefetched_financial_data, number
from .models import (
    StandardAgentResponse,
    Action,
    FundamentalAnalysisData,
    HealthData,
    FundamentalValidationRequest,
    FundamentalValidationReport,
    FundamentalValidationItem,
    FUNDAMENTAL_AGENT_TYPE,
    FUNDAMENTAL_AGENT_VERSION,
    SCHEMA_VERSION,
)

CONFIDENCE_CAP = 0.80
PREFETCHED_DATA_CAP = 0.65
SYNTHETIC_DATA_CAP = 0.55

app = FastAPI(title="Fundamental Agent", version=FUNDAMENTAL_AGENT_VERSION)


class TickerRequest(BaseModel):
    ticker: str
    style: Literal["growth", "value", "dividend"] = "growth"
    prefetched_data: Optional[Dict[str, Any]] = None


def build_response(
    status: str,
    data=None,
    error=None,
    metadata=None,
    correlation_id: Optional[str] = None,
    confidence_score=None,
):
    return StandardAgentResponse(
        status=status,
        version=FUNDAMENTAL_AGENT_VERSION,
        schema_version=SCHEMA_VERSION,
        correlation_id=correlation_id,
        data=data,
        error=error,
        metadata=metadata or {},
        confidence_score=confidence_score,
    )


@app.get("/", response_model=StandardAgentResponse[Dict[str, str]])
def read_root():
    return build_response(status="success", data={"message": "Hello World"})


@app.get("/version", response_model=StandardAgentResponse[Dict[str, Any]])
def version_check():
    return build_response(
        status="success",
        data={
            "agent_type": FUNDAMENTAL_AGENT_TYPE,
            "version": FUNDAMENTAL_AGENT_VERSION,
            "schema_version": SCHEMA_VERSION,
            "api_contract": "multi-agent-trading-api-contract",
        },
        metadata={"required_operational_endpoints": ["/health", "/ready", "/version"]},
    )


@app.get("/ready", response_model=StandardAgentResponse[Dict[str, Any]])
def readiness_check():
    return build_response(
        status="success",
        data={
            "ready": True,
            "analysis_endpoint": "/analyze",
            "validation_endpoint": "/validate/fundamental",
            "supported_styles": ["growth", "value", "dividend"],
            "confidence_cap": CONFIDENCE_CAP,
            "prefetched_data_cap": PREFETCHED_DATA_CAP,
            "synthetic_data_cap": SYNTHETIC_DATA_CAP,
        },
        metadata={"contract_source": "fundamental-agent-runtime-contract"},
    )


@app.get("/health", response_model=StandardAgentResponse[HealthData])
def health():
    return build_response(
        status="success",
        data=HealthData(status="healthy"),
        metadata={"confidence_cap": CONFIDENCE_CAP},
    )


def _cap_confidence(raw_score: Any, source: str, data_quality_score: float) -> float:
    try:
        score = float(raw_score or 0.0)
    except (TypeError, ValueError):
        score = 0.0
    cap = CONFIDENCE_CAP
    if "scanner_prefetch" in source:
        cap = min(cap, PREFETCHED_DATA_CAP)
    if data_quality_score < 0.70:
        cap = min(cap, SYNTHETIC_DATA_CAP)
    return max(0.0, min(score, cap))


def _data_quality_score(request: TickerRequest, analysis_result: Dict[str, Any]) -> float:
    source = analysis_result.get("analysis_source", "fundamental_agent_v2")
    score = 1.0
    if request.prefetched_data:
        score -= 0.20
    if "scanner_prefetch" in source:
        score -= 0.15
    flags = analysis_result.get("risk_flags") or []
    if flags:
        score -= min(0.30, 0.05 * len(flags))
    key_metrics = analysis_result.get("key_metrics") or {}
    if not key_metrics:
        score -= 0.15
    return max(0.0, min(1.0, score))


def _prefetched_to_financial_data(prefetched_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return prefetched_financial_data(prefetched_data)


def _to_response_data(request: TickerRequest, analysis_result: Dict[str, Any]) -> FundamentalAnalysisData:
    action_map = {
        "strong_buy": Action.BUY,
        "buy": Action.BUY,
        "neutral": Action.HOLD,
        "hold": Action.HOLD,
        "sell": Action.SELL,
        "strong_sell": Action.SELL,
    }
    action = action_map.get(analysis_result.get("strength"), Action.HOLD)
    score_details = analysis_result.get("score_details") or {}
    analysis_source = analysis_result.get("analysis_source", "fundamental_agent_v2")
    raw_score = analysis_result.get("score", 0.0)
    data_quality_score = _data_quality_score(request, analysis_result)
    capped_score = _cap_confidence(raw_score, analysis_source, data_quality_score)
    risk_flags = list(analysis_result.get("risk_flags") or [])
    if capped_score < float(raw_score or 0.0):
        risk_flags.append("confidence_capped")
    if data_quality_score < 0.70:
        risk_flags.append("low_data_quality")
    return FundamentalAnalysisData(
        action=action,
        confidence_score=capped_score,
        raw_confidence_score=float(raw_score or 0.0),
        confidence_cap=CONFIDENCE_CAP,
        data_quality_score=data_quality_score,
        validation_status="fundamental_validation_required_before_live",
        reason=analysis_result.get("reasoning", "ไม่สามารถสร้างคำวิเคราะห์ได้"),
        source=analysis_result.get("source") or analysis_result.get("analysis_source") or "fundamental_agent",
        decision_trace={
            **(analysis_result.get("decision_trace") or {}),
            "response_action": action.value, "raw_strength": analysis_result.get("strength"),
            "normalization_status": "recognized" if analysis_result.get("strength") in action_map else "invalid_action",
            "analysis_source": analysis_source, "raw_score": raw_score,
            "capped_confidence": capped_score, "data_quality_score": data_quality_score,
            "confidence_caps": {"base": CONFIDENCE_CAP, "prefetched": PREFETCHED_DATA_CAP, "low_quality": SYNTHETIC_DATA_CAP},
            "input_trace": analysis_result.get("input_trace"),
            "evidence_conflict_review_required": analysis_result.get("evidence_conflict_review_required", False),
        },
        quality_score=score_details.get("quality_score"),
        growth_score=score_details.get("growth_score"),
        valuation_score=score_details.get("valuation_score"),
        financial_health_score=score_details.get("financial_health_score"),
        cash_flow_score=score_details.get("cash_flow_score"),
        sector=analysis_result.get("sector"),
        sector_weights=analysis_result.get("sector_weights") or {},
        risk_flags=risk_flags,
        comparative_analysis=analysis_result.get("comparative_analysis") or {},
        key_metrics=analysis_result.get("key_metrics") or {},
    )


def _growth_score_of(result: Dict[str, Any]) -> float:
    try:
        return float(((result.get("score_details") or {}).get("growth_score")) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _run_analysis_result(request: TickerRequest, correlation_id: Optional[str] = None) -> Dict[str, Any]:
    analysis_result = run_analysis(request.ticker, request.style, correlation_id=correlation_id)
    metrics = analysis_result.get("key_metrics") or {}
    growth_missing = all(number(metrics.get(key)) is None for key in (
        "revenue_3y_cagr", "eps_3y_cagr", "fcf_3y_cagr", "revenue_growth", "eps_growth", "fcf_growth",
    ))
    # Negative or zero growth is real evidence. Do not replace it with a higher score.
    conflict = analysis_result.get("evidence_conflict_review_required") or (
        "cross_source_divergence" in (analysis_result.get("risk_flags") or [])
    )
    if not request.prefetched_data or conflict or ("error" not in analysis_result and not growth_missing):
        return analysis_result
    financials = _prefetched_to_financial_data(request.prefetched_data)
    if not financials:
        return analysis_result
    result = run_fundamental_v2(request.ticker.upper(), financials, request.style)
    result["risk_flags"] = sorted(set(result["risk_flags"]) | set(analysis_result.get("risk_flags") or []))
    result["strength"] = action_from_score(result["score"], result["risk_flags"])
    severe = sorted(SEVERE_FLAGS.intersection(result["risk_flags"]))
    result["decision_trace"]["buy_conditions"][1].update(observed=severe, passed=not bool(severe))
    result["source"] = result["analysis_source"] = "fundamental_engine_v2_with_scanner_prefetch"
    result["input_trace"] = financials.get("Scanner Input Trace")
    result["input_trace"]["fallback_reason"] = analysis_result.get("error") or "primary_growth_evidence_missing"
    result["decision_trace"]["buy_conditions"].append({
        "field": "canonical_prefetch_provenance", "operator": "==", "threshold": True,
        "observed": result["input_trace"]["canonical_history_available"],
        "passed": result["input_trace"]["canonical_history_available"],
        "reason_code": "PREFETCH_HISTORY_UNVERIFIED",
    })
    # Legacy cached raw summaries have no observed fiscal history or verifiable timestamp.
    if not result["input_trace"]["canonical_history_available"]:
        result["risk_flags"].append("prefetch_history_unverified")
        if result["strength"] == "buy":
            result["strength"] = "neutral"
            result["reasoning"] += " BUY withheld: prefetched history provenance is unverified."
    result["decision_trace"]["strength"] = result["strength"]
    return result


@app.post("/analyze", response_model=StandardAgentResponse[FundamentalAnalysisData])
def analyze_ticker(request: TickerRequest, req: Request):
    correlation_id = req.headers.get("X-Correlation-ID")
    analysis_result = _run_analysis_result(request, correlation_id=correlation_id)
    if "error" in analysis_result:
        error_reason = analysis_result["error"]
        error_code = "ANALYSIS_FAILED"
        if error_reason == "ticker_not_found":
            error_code = "TICKER_NOT_FOUND"
        elif error_reason == "data_not_enough":
            error_code = "INSUFFICIENT_DATA"
        elif error_reason == "model_error":
            error_code = "MODEL_ERROR"
        return build_response(
            status="error",
            data=FundamentalAnalysisData(
                action=Action.HOLD,
                confidence_score=0.0,
                reason=error_reason,
                risk_flags=[error_reason],
                source="fundamental_agent",
            ),
            error={"code": error_code, "message": error_reason, "retryable": False},
            correlation_id=correlation_id,
            confidence_score=0.0,
        )
    response_data = _to_response_data(request, analysis_result)
    return build_response(
        status="success",
        data=response_data,
        metadata={
            "style": request.style,
            "ticker": request.ticker.upper(),
            "analysis_source": analysis_result.get("analysis_source", "fundamental_agent_v2"),
            "confidence_cap": CONFIDENCE_CAP,
            "data_quality_score": response_data.data_quality_score,
        },
        correlation_id=correlation_id,
        confidence_score=response_data.confidence_score,
    )


@app.post("/validate/fundamental", response_model=StandardAgentResponse[FundamentalValidationReport])
def validate_fundamental(request: FundamentalValidationRequest, req: Request):
    correlation_id = req.headers.get("X-Correlation-ID")
    results: List[FundamentalValidationItem] = []
    for ticker in request.tickers:
        item_request = TickerRequest(ticker=ticker, style=request.style)
        analysis_result = _run_analysis_result(item_request, correlation_id=correlation_id)
        if "error" in analysis_result:
            results.append(
                FundamentalValidationItem(
                    ticker=ticker.upper(),
                    status="error",
                    confidence_score=0.0,
                    data_quality_score=0.0,
                    action=Action.HOLD,
                    risk_flags=[analysis_result["error"]],
                    passed=False,
                    reason=analysis_result["error"],
                )
            )
            continue
        data = _to_response_data(item_request, analysis_result)
        passed = (
            data.data_quality_score >= request.min_data_quality_score
            and data.confidence_score >= request.min_average_confidence
            and data.confidence_score <= CONFIDENCE_CAP
        )
        results.append(
            FundamentalValidationItem(
                ticker=ticker.upper(),
                status="success",
                confidence_score=data.confidence_score,
                data_quality_score=data.data_quality_score or 0.0,
                action=data.action,
                risk_flags=data.risk_flags,
                passed=passed,
                reason=data.reason,
            )
        )
    tested = len(results)
    passed_count = sum(1 for item in results if item.passed)
    failed_count = tested - passed_count
    avg_confidence = sum(item.confidence_score for item in results) / tested if tested else 0.0
    avg_quality = sum(item.data_quality_score for item in results) / tested if tested else 0.0
    report = FundamentalValidationReport(
        tickers=[ticker.upper() for ticker in request.tickers],
        style=request.style,
        confidence_cap=CONFIDENCE_CAP,
        tested=tested,
        passed_count=passed_count,
        failed_count=failed_count,
        average_confidence=round(avg_confidence, 4),
        average_data_quality_score=round(avg_quality, 4),
        passed=tested > 0 and failed_count == 0 and avg_quality >= request.min_data_quality_score,
        criteria={
            "min_data_quality_score": request.min_data_quality_score,
            "min_average_confidence": request.min_average_confidence,
            "confidence_cap": CONFIDENCE_CAP,
        },
        results=results,
    )
    return build_response(status="success", data=report, correlation_id=correlation_id)
