from fastapi import FastAPI, HTTPException
from fundamental_agent import run_analysis

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/analyze/{ticker}")
def analyze_ticker(ticker: str):
    analysis_result = run_analysis(ticker)
    if analysis_result is None:
        raise HTTPException(status_code=404, detail="Ticker not found or analysis failed.")
    return analysis_result
