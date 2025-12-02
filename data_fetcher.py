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

        data = {}

        # --- Data Extraction with individual error handling ---
        try:
            data["ROE"] = info.get('returnOnEquity')
        except Exception:
            data["ROE"] = None

        try:
            data["Debt to Equity Ratio"] = info.get('debtToEquity')
        except Exception:
            data["Debt to Equity Ratio"] = None

        try:
            data["Profit Margins"] = info.get('profitMargins')
        except Exception:
            data["Profit Margins"] = None

        try:
            data["P/E Ratio"] = info.get('trailingPE')
        except Exception:
            data["P/E Ratio"] = None

        try:
            data["Dividend Yield"] = info.get('dividendYield')
        except Exception:
            data["Dividend Yield"] = None

        # --- Historical Financial Data ---
        financials = stock.financials
        balance_sheet = stock.balance_sheet

        if not financials.empty:
            # Revenue Data
            if 'Total Revenue' in financials.index:
                revenue_data = financials.loc['Total Revenue'].iloc[:4].to_dict()
                data['Historical Revenue'] = {
                    k.strftime('%Y-%m-%d'): v
                    for k, v in revenue_data.items()
                }
            # Net Income Data
            if 'Net Income' in financials.index:
                net_income_data = financials.loc['Net Income'].iloc[:4].to_dict()
                data['Historical Net Income'] = {
                    k.strftime('%Y-%m-%d'): v
                    for k, v in net_income_data.items()
                }

        if not balance_sheet.empty:
            # Total Debt Data
            if 'Total Debt' in balance_sheet.index:
                debt_data = balance_sheet.loc['Total Debt'].iloc[:4].to_dict()
                data['Historical Total Debt'] = {
                    k.strftime('%Y-%m-%d'): v
                    for k, v in debt_data.items()
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
        print(json.dumps(financials, indent=4))
