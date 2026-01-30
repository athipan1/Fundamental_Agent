from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Literal
from .fundamental_agent import run_analysis
from datetime import datetime
from .models import StandardResponse, Action

app = FastAPI()


class TickerRequest(BaseModel):
    ticker: str
    style: Literal["growth", "value", "dividend"] = "growth"


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze_ticker(request: TickerRequest, req: Request):
    """
    Analyzes a stock ticker and returns a standardized analysis response.
    It handles success and failure cases by returning a consistent schema.
    """
    correlation_id = req.headers.get("X-Correlation-ID")
    analysis_result = run_analysis(
        request.ticker,
        request.style,
        correlation_id=correlation_id
    )

    # Check if the analysis failed
    if "error" in analysis_result:
        error_reason = analysis_result["error"]
        error_code = "ANALYSIS_FAILED"  # Default error code

        if error_reason == "ticker_not_found":
            error_code = "TICKER_NOT_FOUND"
        elif error_reason == "data_not_enough":
            error_code = "INSUFFICIENT_DATA"
        elif error_reason == "model_error":
            error_code = "MODEL_ERROR"

        return StandardResponse(
            status="error",
            data={
                "action": Action.HOLD,
                "confidence": 0.0,
                "reason": error_reason
            },
            error={
                "code": error_code,
                "message": error_reason,
                "retryable": False
            }
        )

    # --- Process successful analysis ---
    action_map = {
        "strong_buy": Action.BUY,
        "buy": Action.BUY,
        "neutral": Action.HOLD,
        "sell": Action.SELL,
        "strong_sell": Action.SELL,
    }
    action = action_map.get(analysis_result.get("strength"), Action.HOLD)

    return StandardResponse(
        status="success",
        data={
            "action": action.value,
            "confidence": analysis_result.get("score", 0.0),
            "reason": analysis_result.get("reasoning"),
            "source": "fundamental_agent"
        }
    )
