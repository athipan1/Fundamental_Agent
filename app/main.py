from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from .fundamental_agent import run_analysis

# -------------------------------------------------------------------
# App Metadata
# -------------------------------------------------------------------

app = FastAPI(
    title="Fundamental Analysis Agent",
    version="1.0.0",
    description="Fundamental analysis agent compatible with Orchestrator"
)

AGENT_TYPE = "fundamental"
AGENT_VERSION = "1.0"

# -------------------------------------------------------------------
# Request / Response Models
# -------------------------------------------------------------------

class TickerRequest(BaseModel):
    ticker: str = Field(..., example="AOT.BK")
    style: Literal["growth", "value", "dividend"] = "growth"


class AgentData(BaseModel):
    action: Literal["buy", "sell", "hold"]
    confidence_score: float
    reason: str
    style: str


class AgentResponse(BaseModel):
    status: Literal["success"]
    agent_type: str
    agent_version: str
    ticker: str
    data: AgentData


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def health_check():
    return {"status": "Fundamental Agent is running"}


@app.post("/analyze", response_model=AgentResponse)
def analyze_ticker(request: TickerRequest):
    """
    Perform fundamental analysis and return a standardized
    response compatible with the Orchestrator.
    """

    analysis_result = run_analysis(request.ticker, request.style)

    if not analysis_result:
        raise HTTPException(
            status_code=404,
            detail="Ticker not found or analysis failed"
        )

    # ---------------------------------------------------------------
    # Normalize strength -> action
    # ---------------------------------------------------------------

    action_map = {
        "strong_buy": "buy",
        "buy": "buy",
        "neutral": "hold",
        "sell": "sell",
        "strong_sell": "sell",
    }

    action = action_map.get(
        analysis_result.get("strength", "neutral"),
        "hold"
    )

    # ---------------------------------------------------------------
    # Build Orchestrator-compatible response
    # ---------------------------------------------------------------

    return AgentResponse(
        status="success",
        agent_type=AGENT_TYPE,
        agent_version=AGENT_VERSION,
        ticker=request.ticker,
        data=AgentData(
            action=action,
            confidence_score=analysis_result.get("score", 0.0),
            reason=analysis_result.get("reasoning", ""),
            style=request.style
        )
    )