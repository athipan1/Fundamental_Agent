import json
import urllib.parse
import urllib.request
import yfinance as yf
from .exceptions import TickerNotFound, InsufficientData
from . import cache_handler


def _safe_get_fast_info(stock, key):
    try:
        fast_info = getattr(stock, "fast_info", {}) or {}
        if hasattr(fast_info, "get"):
            return fast_info.get(key)
        return fast_info[key]
    except Exception:
        return None


def _fetch_quote_summary(ticker: str) -> dict:
    symbol = urllib.parse.quote(ticker.upper())
    url = (
        "https://query1.finance.yahoo.com/v7/finance/quote"
        f"?symbols={symbol}"
    )
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; FundamentalAgent/1.0)",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"Yahoo quote fallback failed for {ticker}: {exc}")
        return {}

    results = (((payload.get("quoteResponse") or {}).get("result")) or [])
    return results[0] if results else {}


def _build_data_from_quote_and_fast_info(ticker: str, stock, info: dict) -> dict:
    quote = _fetch_quote_summary(ticker)

    price = (
        info.get("regularMarketPrice")
        or quote.get("regularMarketPrice")
        or quote.get("postMarketPrice")
        or _safe_get_fast_info(stock, "last_price")
    )
    market_cap = info.get("marketCap") or quote.get("marketCap") or _safe_get_fast_info(stock, "market_cap")

    data = {
        "ROE": info.get("returnOnEquity"),
        "Debt to Equity Ratio": info.get("debtToEquity"),
        "Profit Margins": info.get("profitMargins"),
        "P/E Ratio": info.get("trailingPE") or quote.get("trailingPE"),
        "Dividend Yield": info.get("dividendYield") or quote.get("dividendYield"),
        "P/B Ratio": info.get("priceToBook") or quote.get("priceToBook"),
        "EPS": info.get("trailingEps") or quote.get("epsTrailingTwelveMonths"),
        "Revenue Growth": info.get("revenueGrowth"),
        "EPS Growth": info.get("earningsGrowth"),
        "Forward P/E": info.get("forwardPE") or quote.get("forwardPE"),
        "PEG Ratio": info.get("pegRatio"),
        "Operating Cash Flow": info.get("operatingCashflow"),
        "Regular Market Price": price,
        "Market Cap": market_cap,
        "Short Name": info.get("shortName") or quote.get("shortName") or quote.get("longName"),
        "Exchange": quote.get("fullExchangeName") or quote.get("exchange"),
        "Currency": quote.get("currency"),
    }
    return data


def get_financial_data(ticker: str) -> dict:
    """
    Fetches key financial data for a given stock ticker, returning raw numbers.
    It uses yfinance first, then Yahoo quote endpoint/fast_info fallback.

    Args:
        ticker: The stock ticker symbol (e.g., 'AAPL').

    Returns:
        A dictionary containing the financial data.

    Raises:
        TickerNotFound: If the ticker is invalid or no price/identity data is found for it.
        InsufficientData: If some data is found, but key metrics are missing.
    """
    ticker = ticker.upper().strip()
    cache_key = f"financial_data_{ticker}"
    cached_data = cache_handler.load_from_cache(cache_key)
    if cached_data:
        print(f"Cache hit for financial data: {ticker}")
        return cached_data

    print(f"Cache miss for financial data: {ticker}. Fetching from yfinance/Yahoo quote fallback.")
    try:
        stock = yf.Ticker(ticker)
        try:
            info = stock.info or {}
        except Exception as exc:
            print(f"yfinance info failed for {ticker}: {exc}")
            info = {}

        data = _build_data_from_quote_and_fast_info(ticker, stock, info)

        # A real ticker should have at least price, market cap, short name, or exchange.
        identity_fields = [
            data.get("Regular Market Price"),
            data.get("Market Cap"),
            data.get("Short Name"),
            data.get("Exchange"),
        ]
        if all(value is None for value in identity_fields):
            raise TickerNotFound(f"No data found for ticker '{ticker}'. It may be delisted or invalid.")

        # Check if we got any valid analytical data at all.
        core_metrics = [
            data.get("ROE"),
            data.get("Debt to Equity Ratio"),
            data.get("Profit Margins"),
            data.get("P/E Ratio"),
            data.get("Dividend Yield"),
            data.get("P/B Ratio"),
            data.get("EPS"),
            data.get("Revenue Growth"),
            data.get("EPS Growth"),
            data.get("Forward P/E"),
            data.get("PEG Ratio"),
            data.get("Operating Cash Flow"),
        ]
        if all(metric is None for metric in core_metrics):
            # Keep valid identity/price data and allow rule-based analyzer to work
            # with a conservative fallback rather than classifying as ticker_not_found.
            data["Data Quality Warning"] = "fundamental_metrics_sparse"

        # --- Historical Revenue Data ---
        try:
            financials = stock.financials
            if financials is not None and not financials.empty:
                if 'Total Revenue' in financials.index:
                    revenue_data = financials.loc['Total Revenue']
                    # Get the last 4 years of data
                    last_four_years = revenue_data.iloc[:4].to_dict()
                    # Convert Timestamps to strings for JSON compatibility
                    data['Historical Revenue'] = {
                        k.strftime('%Y-%m-%d'): v
                        for k, v in last_four_years.items()
                    }
        except Exception as exc:
            print(f"Historical revenue fetch failed for {ticker}: {exc}")

        # --- Dividend History ---
        try:
            dividends = stock.dividends
            if dividends is not None and not dividends.empty:
                # Get the last 5 years of dividend data
                last_5_years_dividends = dividends.resample('YE').sum().tail(5).to_dict()
                data['Dividend History'] = last_5_years_dividends
        except Exception as exc:
            print(f"Dividend history fetch failed for {ticker}: {exc}")

        # --- Cache successful data fetch ---
        cache_handler.save_to_cache(cache_key, data)
        return data

    except TickerNotFound as e:
        print(f"Data fetching failed for {ticker}: {e}")
        raise
    except Exception as e:
        print(f"An unexpected data fetch error occurred for {ticker}: {e}")
        raise TickerNotFound(f"An unexpected error occurred while fetching data for {ticker}: {e}")


if __name__ == '__main__':
    # --- Example Usage ---
    test_ticker = 'AAPL'
    financials = get_financial_data(test_ticker)

    if financials:
        print(f"Financial Data for {test_ticker}:")
        for key, value in financials.items():
            # The output will now be raw numbers (or None)
            print(f"- {key}: {value} (type: {type(value).__name__})")
