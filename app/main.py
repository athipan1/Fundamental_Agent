from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Literal, Dict, Optional, Any, List
from .fundamental_agent import run_analysis
from .fundamental_engine_v2 import run_fundamental_v2
from .models import (
    StandardAgentResponse,
    Action,
    FundamentalAnalysisData,
    HealthData,
    FundamentalValidationRequest,
    FundamentalValidationReport,
    FundamentalValidationItem,
)

CONFIDENCE_CAP = 0.80
PREFETCHED_DATA_CAP = 0.65
SYNTHETIC_DATA_CAP = 0.55

app = FastAPI()


class TickerRequest(BaseModel):
    ticker: str
    style: Literal["growth", "value", "dividend"] = "growth"
    prefetched_data: Optional[Dict[str, Any]] = None


@app.get("/", response_model=StandardAgentResponse[Dict[str, str]])
def read_root():
    return StandardAgentResponse(status="success", data={"message": "Hello World"})


@app.get("/health", response_model=StandardAgentResponse[HealthData])
def health():
    return StandardAgentResponse(
        status="success",
        version="1.0.0",
        data=HealthData(status="healthy"),
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


def _as_decimal(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        value = float(value)
        return value / 100.0 if abs(value) > 1 else value
    except (TypeError, ValueError):
        return None


def _synthetic_history_from_growth(growth: Any, periods: int = 3) -> Dict[str, float]:
    growth = _as_decimal(growth)
    if growth is None or growth <= -0.95:
        return {}
    end_value = 1.0 + growth
    return {
        "2021-12-31": 1.0,
        "2022-12-31": max(0.01, 1.0 + (growth * 1 / max(1, periods))),
        "2023-12-31": max(0.01, 1.0 + (growth * 2 / max(1, periods))),
        "2024-12-31": max(0.01, end_value),
    }


def _synthetic_quarterly_from_growth(growth: Any) -> Dict[str, float]:
    growth = _as_decimal(growth)
    if growth is None or growth <= -0.95:
        return {}
    return {
        "2024-06-30": 1.0,
        "2024-09-30": max(0.01, 1.0 + growth),
    }


def _prefetched_to_financial_data(prefetched_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not prefetched_data:
        return {}
    metadata = prefetched_data.get("metadata") or {}
    raw_scores = prefetched_data.get("raw_scores") or metadata.get("raw_scores") or {}
    growth_metrics = metadata.get("growth_metrics") or {}
    revenue_growth = raw_scores.get("revenue_3y_cagr")
    if revenue_growth is None:
        revenue_growth = raw_scores.get("revenue_cagr")
    revenue_growth = _as_decimal(revenue_growth)
    eps_growth = _as_decimal(raw_scores.get("eps_growth"))
    fcf_growth = _as_decimal(raw_scores.get("fcf_growth") or raw_scores.get("fcf_3y_cagr"))
    qoq_revenue_growth = _as_decimal(raw_scores.get("qoq_revenue_growth"))
    qoq_eps_growth = _as_decimal(raw_scores.get("qoq_eps_growth"))
    qoq_fcf_growth = _as_decimal(raw_scores.get("qoq_fcf_growth"))
    return {
        "ROE": raw_scores.get("roe"),
        "ROA": raw_scores.get("roa"),
        "Debt to Equity Ratio": raw_scores.get("debt_to_equity"),
        "Profit Margins": raw_scores.get("profit_margins"),
        "P/E Ratio": raw_scores.get("pe_ratio"),
        "PEG Ratio": raw_scores.get("peg_ratio"),
        "P/B Ratio": raw_scores.get("pb_ratio"),
        "Revenue Growth": revenue_growth,
        "EPS Growth": eps_growth,
        "FCF Growth": fcf_growth,
        "Historical Revenue": _synthetic_history_from_growth(revenue_growth),
        "Historical EPS": _synthetic_history_from_growth(eps_growth),
        "Historical Free Cash Flow": _synthetic_history_from_growth(fcf_growth),
        "Historical FCF": _synthetic_history_from_growth(fcf_growth),
        "Quarterly Revenue Growth": qoq_revenue_growth,
        "Quarterly EPS Growth": qoq_eps_growth,
        "Quarterly FCF Growth": qoq_fcf_growth,
        "Quarterly Revenue": _synthetic_quarterly_from_growth(qoq_revenue_growth),
        "Quarterly EPS": _synthetic_quarterly_from_growth(qoq_eps_growth),
        "Quarterly Free Cash Flow": _synthetic_quarterly_from_growth(qoq_fcf_growth),
        "Operating Cash Flow": raw_scores.get("operating_cash_flow") or raw_scores.get("free_cash_flow"),
        "Free Cash Flow": raw_scores.get("free_cash_flow"),
        "Market Cap": raw_scores.get("market_cap"),
        "Sector": metadata.get("sector") or prefetched_data.get("sector"),
        "Exchange": prefetched_data.get("exchange") or metadata.get("exchange"),
        "Short Name": prefetched_data.get("symbol") or prefetched_data.get("ticker"),
        "Data Quality Warning": "scanner_prefetched_data",
        "Scanner Growth Metrics": growth_metrics,
    }


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
    source = analysis_result.get("analysis_source", "fundamental_agent_v2")
    raw_score = analysis_result.get("score", 0.0)
    data_quality_score = _data_quality_score(request, analysis_result)
    capped_score = _cap_confidence(raw_score, source, data_quality_score)
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
        source=source,
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
    if request.prefetched_data and ("error" in analysis_result or _growth_score_of(analysis_result) <= 0.0):
        prefetched_financials = _prefetched_to_financial_data(request.prefetched_data)
        if prefetched_financials:
            prefetch_result = run_fundamental_v2(
                request.ticker.upper(),
                prefetched_financials,
                request.style,
            )
            prefetch_result["analysis_source"] = "fundamental_engine_v2_with_scanner_prefetch"
            if "error" in analysis_result or _growth_score_of(prefetch_result) >= _growth_score_of(analysis_result):
                analysis_result = prefetch_result
    return analysis_result


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
        return StandardAgentResponse(
            status="error",
            version="1.0.0",
            data=FundamentalAnalysisData(
                action=Action.HOLD,
                confidence_score=0.0,
                reason=error_reason,
                risk_flags=[error_reason],
                source="fundamental_agent_v2",
            ),
            error={"code": error_code, "message": error_reason, "retryable": False},
        )
    response_data = _to_response_data(request, analysis_result)
    return StandardAgentResponse(
        status="success",
        version="1.0.0",
        data=response_data,
        metadata={
            "style": request.style,
            "ticker": request.ticker.upper(),
            "analysis_source": analysis_result.get("analysis_source", "fundamental_agent_v2"),
            "confidence_cap": CONFIDENCE_CAP,
            "data_quality_score": response_data.data_quality_score,
        },
    )


@app.post("/validate/fundamental", response_model=StandardAgentResponse[FundamentalValidationReport])
def validate_fundamental(request: FundamentalValidationRequest):
    results: List[FundamentalValidationItem] = []
    for ticker in request.tickers:
        item_request = TickerRequest(ticker=ticker, style=request.style)
        analysis_result = _run_analysis_result(item_request)
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
    return StandardAgentResponse(status="success", version="1.0.0", data=report)
