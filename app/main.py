from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Literal, Dict, Optional, Any
from .fundamental_agent import run_analysis
from .fundamental_engine_v2 import run_fundamental_v2
from .models import StandardAgentResponse, Action, FundamentalAnalysisData, HealthData

app = FastAPI()


class TickerRequest(BaseModel):
    ticker: str
    style: Literal["growth", "value", "dividend"] = "growth"
    prefetched_data: Optional[Dict[str, Any]] = None


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


def _prefetched_to_financial_data(prefetched_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not prefetched_data:
        return {}
    metadata = prefetched_data.get("metadata") or {}
    raw_scores = prefetched_data.get("raw_scores") or metadata.get("raw_scores") or {}
    growth_metrics = metadata.get("growth_metrics") or {}

    revenue_growth = raw_scores.get("revenue_3y_cagr")
    if revenue_growth is None:
        revenue_growth = raw_scores.get("revenue_cagr")
        if isinstance(revenue_growth, (int, float)) and abs(revenue_growth) > 1:
            revenue_growth = revenue_growth / 100.0

    eps_growth = raw_scores.get("eps_growth")
    fcf_growth = raw_scores.get("fcf_growth") or raw_scores.get("fcf_3y_cagr")
    qoq_revenue_growth = raw_scores.get("qoq_revenue_growth")
    qoq_eps_growth = raw_scores.get("qoq_eps_growth")
    qoq_fcf_growth = raw_scores.get("qoq_fcf_growth")

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
        "Quarterly Revenue Growth": qoq_revenue_growth,
        "Quarterly EPS Growth": qoq_eps_growth,
        "Quarterly FCF Growth": qoq_fcf_growth,
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
    return FundamentalAnalysisData(
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
    )


@app.post("/analyze", response_model=StandardAgentResponse[FundamentalAnalysisData])
def analyze_ticker(request: TickerRequest, req: Request):
    """
    Analyzes a stock ticker and returns a standardized analysis response.
    If live market data is sparse, Manager_Agent may provide Scanner_Agent
    prefetched fundamentals so v2 scores are still available.
    """
    correlation_id = req.headers.get("X-Correlation-ID")
    analysis_result = run_analysis(
        request.ticker,
        request.style,
        correlation_id=correlation_id
    )

    if "error" in analysis_result and request.prefetched_data:
        prefetched_financials = _prefetched_to_financial_data(request.prefetched_data)
        if prefetched_financials:
            analysis_result = run_fundamental_v2(request.ticker.upper(), prefetched_financials, request.style)
            analysis_result["analysis_source"] = "fundamental_engine_v2_with_scanner_prefetch"

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

    return StandardAgentResponse(
        status="success",
        data=_to_response_data(request, analysis_result),
        metadata={
            "style": request.style,
            "ticker": request.ticker.upper(),
            "analysis_source": analysis_result.get("analysis_source", "fundamental_agent_v2"),
        }
    )
