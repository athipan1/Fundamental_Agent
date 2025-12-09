import yfinance as yf


def get_financial_data(ticker: str) -> dict:
    """
    Fetches key financial data for a given stock ticker, returning raw numbers.

    Args:
        ticker: The stock ticker symbol (e.g., 'AAPL').

    Returns:
        A dictionary containing the financial data, or None if the ticker is
        invalid.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # --- Data Extraction ---
        # Fetch raw numerical data, defaulting to None if not available.
        roe = info.get('returnOnEquity')
        debt_to_equity = info.get('debtToEquity')
        profit_margins = info.get('profitMargins')
        pe_ratio = info.get('trailingPE')
        dividend_yield = info.get('dividendYield')
        pb_ratio = info.get('priceToBook')
        eps = info.get('trailingEps')
        revenue_growth = info.get('revenueGrowth')
        eps_growth = info.get('earningsGrowth')
        forward_pe = info.get('forwardPE')
        peg_ratio = info.get('pegRatio')
        operating_cashflow = info.get('operatingCashflow')

        data = {
            "ROE": roe,
            "Debt to Equity Ratio": debt_to_equity,
            "Profit Margins": profit_margins,
            "P/E Ratio": pe_ratio,
            "Dividend Yield": dividend_yield,
            "P/B Ratio": pb_ratio,
            "EPS": eps,
            "Revenue Growth": revenue_growth,
            "EPS Growth": eps_growth,
            "Forward P/E": forward_pe,
            "PEG Ratio": peg_ratio,
            "Operating Cash Flow": operating_cashflow,
        }

        # --- Historical Revenue Data ---
        financials = stock.financials
        if not financials.empty:
            revenue_data = financials.loc['Total Revenue']
            # Get the last 4 years of data
            last_four_years = revenue_data.iloc[:4].to_dict()
            # Convert Timestamps to strings for JSON compatibility
            data['Historical Revenue'] = {
                k.strftime('%Y-%m-%d'): v
                for k, v in last_four_years.items()
            }

        # Check if we got any valid data at all
        if all(value is None for value in data.values()):
            print(f"Warning: Could not retrieve data for {ticker}.")
            return None

        return data

    except Exception as e:
        print(f"An error occurred while fetching data for {ticker}: {e}")
        return None


if __name__ == '__main__':
    # --- Example Usage ---
    test_ticker = 'AAPL'
    financials = get_financial_data(test_ticker)

    if financials:
        print(f"Financial Data for {test_ticker}:")
        for key, value in financials.items():
            # The output will now be raw numbers (or None)
            print(f"- {key}: {value} (type: {type(value).__name__})")
