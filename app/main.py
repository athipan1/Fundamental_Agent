from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Literal, Dict
from .fundamental_agent import run_analysis
from .models import StandardAgentResponse, Action, FundamentalAnalysisData, HealthData

app = FastAPI()


class TickerRequest(BaseModel):
    ticker: str
    style: Literal["growth", "value", "dividend"] = "growth"


@app.get("/", response_model=StandardAgentResponse[Dict[str, str]])
def read_root():
    return StandardAgentResponse(
        status="success",
        data={"message": "Hello World"}
    )


@app.get("/health", response_model=StandardAgentResponse[HealthData])
def health():
    return StandardAgentResponse(
        status="success",
        data=HealthData(status="healthy")
    )


@app.post("/analyze", response_model=StandardAgentResponse[FundamentalAnalysisData])
def analyze_ticker(request: TickerRequest, req: Request):
    """
    Analyzes a stock ticker and returns a standardized analysis response.
    v2 returns detailed factor scores, sector-aware scoring context,
    peer comparison metadata, and risk flags for Manager_Agent.
    """
    correlation_id = req.headers.get("X-Correlation-ID")
    analysis_result = run_analysis(
        request.ticker,
        request.style,
        correlation_id=correlation_id
    )

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
            data=FundamentalAnalysisData(
                action=Action.HOLD,
                confidence_score=0.0,
                reason=error_reason,
                risk_flags=[error_reason],
                source="fundamental_agent_v2"
            ),
            error={
                "code": error_code,
                "message": error_reason,
                "retryable": False
            }
        )

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

    return StandardAgentResponse(
        status="success",
        data=FundamentalAnalysisData(
            action=action,
            confidence_score=analysis_result.get("score", 0.0),
            reason=analysis_result.get("reasoning", "ไม่สามารถสร้างคำวิเคราะห์ได้"),
            source=analysis_result.get("analysis_source", "fundamental_agent_v2"),
            quality_score=score_details.get("quality_score"),
            growth_score=score_details.get("growth_score"),
            valuation_score=score_details.get("valuation_score"),
            financial_health_score=score_details.get("financial_health_score"),
            cash_flow_score=score_details.get("cash_flow_score"),
            sector=analysis_result.get("sector"),
            sector_weights=analysis_result.get("sector_weights") or {},
            risk_flags=analysis_result.get("risk_flags") or [],
            comparative_analysis=analysis_result.get("comparative_analysis") or {},
            key_metrics=analysis_result.get("key_metrics") or {},
        ),
        metadata={
            "style": request.style,
            "ticker": request.ticker.upper(),
            "analysis_source": analysis_result.get("analysis_source", "fundamental_agent_v2"),
        }
    )
