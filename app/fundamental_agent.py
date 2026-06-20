import argparse
import json
from typing import Optional
from .data_fetcher import get_financial_data
from .analyzer import analyze_financials
from .rule_based_analyzer import run_rule_based_analysis
from .fundamental_engine_v2 import run_fundamental_v2
from .exceptions import TickerNotFound, InsufficientData, ModelError
from . import cache_handler


def _merge_llm_reasoning(v2_result: dict, llm_result: Optional[dict]) -> dict:
    if not llm_result:
        return v2_result
    llm_reason = llm_result.get("reasoning")
    if llm_reason:
        v2_result["reasoning"] = f"{v2_result.get('reasoning', '')} บทวิเคราะห์เสริม: {llm_reason}"
        v2_result["llm_reasoning"] = llm_reason
    v2_result["analysis_source"] = "fundamental_engine_v2_with_llm" if llm_reason else v2_result.get("analysis_source")
    return v2_result


def run_analysis(ticker: str, style: str = "growth", correlation_id: Optional[str] = None):
    """
    Runs the fundamental analysis for a given stock ticker.
    It uses a cache to avoid redundant API calls for both data and final analysis.
    v2 always computes deterministic structured scores first, then optionally
    appends LLM reasoning when available.
    """
    log_prefix = f"[{correlation_id}] " if correlation_id else ""
    ticker = ticker.upper().strip()
    print(f"{log_prefix}--- Starting fundamental analysis for {ticker} (Style: {style}) ---")

    cache_key = f"analysis_v2_{ticker}_{style}"
    cached_analysis = cache_handler.load_from_cache(cache_key)
    if cached_analysis:
        print(f"{log_prefix}Cache hit for final v2 analysis: {ticker} (Style: {style})")
        return cached_analysis

    print(f"{log_prefix}Cache miss for final v2 analysis: {ticker} (Style: {style}). Running full analysis.")
    try:
        print(f"{log_prefix}Fetching financial data for {ticker}...")
        financial_data = get_financial_data(ticker)
        print(f"{log_prefix}Data fetched successfully.")

        print(f"{log_prefix}Running deterministic fundamental engine v2...")
        v2_result = run_fundamental_v2(ticker, financial_data, style)
        print(f"{log_prefix}Fundamental engine v2 completed.")

        # Optional LLM explanation: never allow model failure to erase v2 scores.
        try:
            llm_result = analyze_financials(ticker, financial_data, style)
            print(f"{log_prefix}LLM analysis completed successfully.")
            analysis_result = _merge_llm_reasoning(v2_result, llm_result)
        except ModelError as e:
            print(f"{log_prefix}LLM analysis failed: {e}. Keeping v2 deterministic score.")
            analysis_result = v2_result
        except Exception as e:
            print(f"{log_prefix}LLM analysis unexpected failure: {e}. Keeping v2 deterministic score.")
            analysis_result = v2_result

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
            fallback = run_rule_based_analysis(ticker, financial_data, style)
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
