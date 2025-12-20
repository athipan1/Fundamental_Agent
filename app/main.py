from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .fundamental_agent import run_analysis

app = FastAPI()


from typing import Literal


class TickerRequest(BaseModel):
    ticker: str
    style: Literal["growth", "value", "dividend"] = "growth"


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/analyze")
def analyze_ticker(request: TickerRequest):
    analysis_result = run_analysis(request.ticker, request.style)
    if analysis_result is None:
        raise HTTPException(status_code=404, detail="Ticker not found or analysis failed.")

    # Transform the result to the format expected by the Orchestrator
    orchestrator_response = {
        "ticker": request.ticker,
        "recommendation": analysis_result.get("strength"),
        "confidence_score": analysis_result.get("score"),
        "analysis_summary": analysis_result.get("reasoning"),
        "full_report": analysis_result,
    }

    return orchestrator_response
