from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fundamental_agent import run_analysis

app = FastAPI()


class TickerRequest(BaseModel):
    ticker: str


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/analyze")
def analyze_ticker(request: TickerRequest):
    analysis_result = run_analysis(request.ticker)
    if analysis_result is None:
        raise HTTPException(status_code=404, detail="Ticker not found or analysis failed.")
    return analysis_result
