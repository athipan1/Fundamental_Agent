import argparse
import json
from typing import Any, Dict, Optional
from .data_fetcher import get_financial_data
from .analyzer import analyze_financials
from .rule_based_analyzer import run_rule_based_analysis
from .fundamental_engine_v2 import run_fundamental_v2
from .exceptions import TickerNotFound, InsufficientData, ModelError
from . import cache_handler


EVIDENCE_CACHE_VERSION = "fundamental-evidence-v1"


def _merge_llm_reasoning(v2_result: dict, llm_result: Optional[dict]) -> dict:
    if not llm_result:
        return v2_result
    if "source" in llm_result and "score" not in v2_result:
        return llm_result
    llm_reason = llm_result.get("reasoning")
    if llm_reason:
        v2_result["reasoning"] = f"{v2_result.get('reasoning', '')} บทวิเคราะห์เสริม: {llm_reason}"
        v2_result["llm_reasoning"] = llm_reason
    if llm_reason:
        v2_result["analysis_source"] = "fundamental_engine_v2_with_llm"
    else:
        v2_result.update(llm_result)
    return v2_result


def attach_financial_evidence(
    analysis_result: Dict[str, Any],
    financial_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Preserve raw financial evidence needed by Scanner and Manager.

    This helper does not assign a strategy bucket. It only ensures that metrics
    already fetched by Fundamental_Agent survive into the standard response.
    """
    result = dict(analysis_result or {})
    key_metrics = dict(result.get("key_metrics") or {})
    metric_map = {
        "roe": "ROE",
        "roa": "ROA",
        "roic": "ROIC",
        "profit_margins": "Profit Margins",
        "operating_margin": "Operating Margin",
        "gross_margin": "Gross Margin",
        "fcf_margin": "FCF Margin",
        "cash_conversion": "Cash Conversion",
        "interest_coverage": "Interest Coverage",
        "eps": "EPS",
        "revenue_growth": "Revenue Growth",
        "eps_growth": "EPS Growth",
        "fcf_growth": "FCF Growth",
        "pe_ratio": "P/E Ratio",
        "forward_pe": "Forward P/E",
        "peg_ratio": "PEG Ratio",
        "pb_ratio": "P/B Ratio",
        "debt_to_equity": "Debt to Equity Ratio",
        "operating_cash_flow": "Operating Cash Flow",
        "free_cash_flow": "Free Cash Flow",
        "net_income": "Net Income",
        "market_cap": "Market Cap",
        "net_cash": "Net Cash",
        "dividend_yield": "Dividend Yield",
        "dividend_rate": "Dividend Rate",
        "payout_ratio": "Payout Ratio",
    }
    for output_key, source_key in metric_map.items():
        source_value = financial_data.get(source_key)
        if source_value is not None and key_metrics.get(output_key) is None:
            key_metrics[output_key] = source_value

    result["key_metrics"] = key_metrics
    result["financial_data_provenance"] = {
        "provider": "yfinance_yahoo_quote",
        "sector": financial_data.get("Sector"),
        "industry": financial_data.get("Industry"),
        "exchange": financial_data.get("Exchange"),
        "currency": financial_data.get("Currency"),
        "data_quality_warning": financial_data.get("Data Quality Warning"),
        "preserved_metric_fields": sorted(
            key for key, value in key_metrics.items() if value is not None
        ),
        "bucket_decision_authority": "manager",
    }
    result["strategy_bucket_hint"] = None
    result["bucket_decision_authority"] = "manager"
    result["manager_decision_required"] = True
    return result


def run_analysis(ticker: str, style: str = "growth", correlation_id: Optional[str] = None):
    """Run deterministic fundamental analysis plus optional LLM reasoning."""
    log_prefix = f"[{correlation_id}] " if correlation_id else ""
    ticker = ticker.upper().strip()
    print(f"{log_prefix}--- Starting fundamental analysis for {ticker} (Style: {style}) ---")

    cache_key = f"analysis_{EVIDENCE_CACHE_VERSION}_{ticker}_{style}"
    cached_analysis = cache_handler.load_from_cache(cache_key)
    if cached_analysis:
        print(f"{log_prefix}Cache hit for evidence-aware analysis: {ticker} (Style: {style})")
        return cached_analysis

    print(f"{log_prefix}Cache miss for evidence-aware analysis: {ticker} (Style: {style}). Running full analysis.")
    try:
        print(f"{log_prefix}Fetching financial data for {ticker}...")
        financial_data = get_financial_data(ticker)
        print(f"{log_prefix}Data fetched successfully.")

        print(f"{log_prefix}Running deterministic fundamental engine v2...")
        v2_result = attach_financial_evidence(
            run_fundamental_v2(ticker, financial_data, style),
            financial_data,
        )
        print(f"{log_prefix}Fundamental engine v2 completed.")

        try:
            llm_result = analyze_financials(ticker, financial_data, style)
            print(f"{log_prefix}LLM analysis completed successfully.")
            analysis_result = _merge_llm_reasoning(v2_result, llm_result)
        except ModelError as e:
            print(f"{log_prefix}LLM analysis failed: {e}. Using deterministic result.")
            analysis_result = v2_result
        except Exception as e:
            print(f"{log_prefix}LLM analysis unexpected failure: {e}. Using deterministic result.")
            analysis_result = v2_result

        analysis_result = attach_financial_evidence(analysis_result, financial_data)
        cache_handler.save_to_cache(cache_key, analysis_result)
        return analysis_result

    except TickerNotFound:
        print(f"{log_prefix}Analysis failed: Ticker '{ticker}' not found.")
        return {"error": "ticker_not_found"}
    except InsufficientData:
        print(f"{log_prefix}Analysis failed: Insufficient data for '{ticker}'.")
        return {"error": "data_not_enough"}
    except Exception as e:
        print(f"{log_prefix}An unexpected error occurred during analysis for '{ticker}': {e}")
        try:
            financial_data = get_financial_data(ticker)
            fallback = attach_financial_evidence(
                run_rule_based_analysis(ticker, financial_data, style),
                financial_data,
            )
            fallback["analysis_source"] = "legacy_rule_based_emergency_fallback"
            return fallback
        except Exception:
            return {"error": "analysis_failed"}


def main():
    """Command line interface for running fundamental analysis."""
    parser = argparse.ArgumentParser(description="Run fundamental analysis for a ticker.")
    parser.add_argument("ticker")
    parser.add_argument("--style", default="growth", choices=["growth", "value", "dividend"])
    args = parser.parse_args()
    result = run_analysis(args.ticker, args.style)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
