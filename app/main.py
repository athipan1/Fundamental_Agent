from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Literal

from .fundamental_agent import run_analysis


app = FastAPI(
    title="Fundamental Analysis Agent",
    version="1.0.0",
)


class TickerRequest(BaseModel):
    ticker: str
    style: Literal["growth", "value", "dividend"] = "growth"


@app.get("/")
def read_root():
    return {"status": "Fundamental Agent is running"}


@app.post("/analyze")
def analyze_ticker(request: TickerRequest):
    """
    Analyze a stock ticker and return a response
    compatible with the Orchestrator.
    """
    analysis_result = run_analysis(request.ticker, request.style)

    if analysis_result is None:
        raise HTTPException(
            status_code=404,
            detail="Ticker not found or analysis failed.",
        )

    # Map agent-specific strength to orchestrator action
    action_map = {
        "strong_buy": "buy",
        "buy": "buy",
        "neutral": "hold",
        "sell": "sell",
        "strong_sell": "sell",
    }

    action = action_map.get(
        analysis_result.get("strength"),
        "hold",
    )

    return {
        "data": {
            "action": action,
            "confidence_score": analysis_result.get("score", 0.0),
            "reason": analysis_result.get("reasoning", ""),
        }
    }