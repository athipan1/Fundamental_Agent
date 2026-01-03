from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Literal
from .fundamental_agent import run_analysis

app = FastAPI()


class TickerRequest(BaseModel):
    ticker: str
    style: Literal["growth", "value", "dividend"] = "growth"


@app.get("/")
def read_root():
    return {"Hello": "World"}


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
        return {
            "analysis": {
                "action": "hold",
                "confidence": 0.0,
                "reason": error_reason,
                "source": "fundamental_agent"
            }
        }

    # --- Process successful analysis ---
    action_map = {
        "strong_buy": "buy",
        "buy": "buy",
        "neutral": "hold",
        "sell": "sell",
        "strong_sell": "sell",
    }
    action = action_map.get(analysis_result.get("strength"), "hold")

    return {
        "analysis": {
            "action": action,
            "confidence": analysis_result.get("score", 0.0),
            "reason": analysis_result.get("reasoning"),
            "source": "fundamental_agent"
        }
    }
