import argparse
import json
from data_fetcher import get_financial_data
from analyzer import analyze_financials


def main():
    """
    The main function for the Fundamental Analysis Agent.
    It takes a stock ticker, fetches its financial data, analyzes it,
    and prints the final analysis as a JSON object.
    """
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="Fundamental Financial Analysis Agent"
    )
    parser.add_argument(
        "ticker",
        type=str,
        help="The stock ticker symbol to analyze (e.g., AAPL, GOOGL)."
    )
    args = parser.parse_args()

    ticker = args.ticker.upper()
    print(f"--- Starting fundamental analysis for {ticker} ---")

    # --- Step 1: Fetch Data ---
    print(f"Fetching financial data for {ticker}...")
    financial_data = get_financial_data(ticker)

    if not financial_data:
        print(f"Could not retrieve data for {ticker}. Exiting.")
        return

    print("Data fetched successfully.")
    print(json.dumps(financial_data, indent=2))

    # --- Step 2: Analyze Data ---
    print(f"Analyzing financial data for {ticker}...")
    analysis_result = analyze_financials(ticker, financial_data)

    if not analysis_result:
        print("Analysis could not be completed. Exiting.")
        return

    # --- Step 3: Display Result ---
    print("\n--- ✅ Fundamental Analysis Complete ---")
    print(json.dumps(analysis_result, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()
