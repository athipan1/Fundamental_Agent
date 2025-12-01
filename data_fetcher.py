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
        revenue_growth = info.get('revenueGrowth')
        profit_margins = info.get('profitMargins')

        data = {
            "ROE": roe,
            "Debt to Equity Ratio": debt_to_equity,
            "Quarterly Revenue Growth (yoy)": revenue_growth,
            "Profit Margins": profit_margins
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
