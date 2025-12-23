from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal, Optional
import logging

from .fundamental_agent import run_analysis

# ------------------------------------------------------------------------------
# App setup
# ------------------------------------------------------------------------------
app = FastAPI(
    title="Fundamental Agent",
    description="AI Fundamental Analysis Agent for Orchestrator",
    version="1.0.0",
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Request / Response Models
# ------------------------------------------------------------------------------

class TickerRequest(BaseModel):
    ticker: str = Field(..., example="AAPL")
    style: Literal["growth", "value", "dividend"] = "growth"


class FundamentalData(BaseModel):
    action: Literal["buy", "sell", "hold"]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reason: Optional[str] = None


class FundamentalAgentResponse(BaseModel):
    data: FundamentalData


# ------------------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------------------

@app.get("/")
def health_check():
    return {"status": "ok", "service": "fundamental-agent"}


# ------------------------------------------------------------------------------
# Core endpoint (used by Orchestrator)
# ------------------------------------------------------------------------------

@app.post("/analyze", response_model=FundamentalAgentResponse)
def analyze_ticker(request: TickerRequest):
    """
    Analyze a ticker using fundamental analysis logic and
    return a response that strictly follows the Orchestrator contract.
    """
    logger.info(
        "Received analysis request: ticker=%s, style=%s",
        request.ticker,
        request.style,
    )

    analysis_result = run_analysis(request.ticker, request.style)

    if analysis_result is None:
        logger.error("Analysis failed for ticker=%s", request.ticker)
        raise HTTPException(
            status_code=404,
            detail="Ticker not found or analysis failed",
        )

    # --------------------------------------------------------------------------
    # Map internal AI output → Orchestrator action contract
    # --------------------------------------------------------------------------
    strength = analysis_result.get("strength", "neutral")
    score = analysis_result.get("score", 0.0)
    reasoning = analysis_result.get("reasoning", "")

    action_map = {
        "strong_buy": "buy",
        "buy": "buy",
        "neutral": "hold",
        "hold": "hold",
        "sell": "sell",
        "strong_sell": "sell",
    }

    action = action_map.get(strength, "hold")

    response = FundamentalAgentResponse(
        data=FundamentalData(
            action=action,
            confidence_score=float(score),
            reason=reasoning,
        )
    )

    logger.info(
        "Analysis completed: ticker=%s, action=%s, confidence=%s",
        request.ticker,
        action,
        score,
    )

    return response