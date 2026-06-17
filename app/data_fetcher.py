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


def _safe_ratio(numerator, denominator):
    try:
        if numerator is None or denominator in (None, 0):
            return None
        return float(numerator) / float(denominator)
    except Exception:
        return None


def _series_to_recent_dict(series, limit: int = 4) -> dict:
    try:
        if series is None or series.empty:
            return {}
        recent = series.dropna().iloc[:limit].to_dict()
        return {
            k.strftime('%Y-%m-%d') if hasattr(k, 'strftime') else str(k): v
            for k, v in recent.items()
        }
    except Exception:
        return {}


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
    operating_cash_flow = info.get("operatingCashflow")
    free_cash_flow = info.get("freeCashflow")
    total_debt = info.get("totalDebt")
    total_cash = info.get("totalCash")
    ebitda = info.get("ebitda")
    enterprise_value = info.get("enterpriseValue") or quote.get("enterpriseValue")
    total_revenue = info.get("totalRevenue")
    gross_profits = info.get("grossProfits")
    net_income = (
        info.get("netIncomeToCommon")
        or info.get("netIncome")
        or info.get("netIncomeApplicableToCommonShares")
    )

    fcf_margin = _safe_ratio(free_cash_flow, total_revenue)
    cash_conversion = _safe_ratio(free_cash_flow, net_income)
    gross_margin = _safe_ratio(gross_profits, total_revenue) or info.get("grossMargins")
    roic_proxy = _safe_ratio(ebitda, enterprise_value)
    interest_coverage_proxy = _safe_ratio(ebitda, info.get("interestExpense") or info.get("totalInterestExpense"))
    net_cash = None
    if total_cash is not None or total_debt is not None:
        net_cash = float(total_cash or 0) - float(total_debt or 0)

    data = {
        "ROE": info.get("returnOnEquity"),
        "ROA": info.get("returnOnAssets"),
        "ROIC": info.get("returnOnCapital") or info.get("returnOnInvestedCapital") or roic_proxy,
        "Debt to Equity Ratio": info.get("debtToEquity"),
        "Profit Margins": info.get("profitMargins"),
        "Operating Margin": info.get("operatingMargins"),
        "Gross Margin": gross_margin,
        "FCF Margin": fcf_margin,
        "Cash Conversion": cash_conversion,
        "Interest Coverage": info.get("interestCoverage") or interest_coverage_proxy,
        "P/E Ratio": info.get("trailingPE") or quote.get("trailingPE"),
        "Dividend Yield": info.get("dividendYield") or quote.get("dividendYield"),
        "P/B Ratio": info.get("priceToBook") or quote.get("priceToBook"),
        "EPS": info.get("trailingEps") or quote.get("epsTrailingTwelveMonths"),
        "Revenue Growth": info.get("revenueGrowth"),
        "EPS Growth": info.get("earningsGrowth"),
        "Quarterly Revenue Growth": info.get("revenueQuarterlyGrowth") or info.get("quarterlyRevenueGrowth"),
        "Quarterly EPS Growth": info.get("earningsQuarterlyGrowth") or info.get("quarterlyEarningsGrowthYOY"),
        "Forward P/E": info.get("forwardPE") or quote.get("forwardPE"),
        "PEG Ratio": info.get("pegRatio"),
        "Operating Cash Flow": operating_cash_flow,
        "Free Cash Flow": free_cash_flow,
        "Net Income": net_income,
        "Total Revenue": total_revenue,
        "Total Debt": total_debt,
        "Total Cash": total_cash,
        "Net Cash": net_cash,
        "EBITDA": ebitda,
        "Enterprise Value": enterprise_value,
        "Regular Market Price": price,
        "Market Cap": market_cap,
        "Sector": info.get("sector"),
        "Industry": info.get("industry"),
        "Short Name": info.get("shortName") or quote.get("shortName") or quote.get("longName"),
        "Exchange": quote.get("fullExchangeName") or quote.get("exchange"),
        "Currency": quote.get("currency"),
    }
    return data


def get_financial_data(ticker: str) -> dict:
    """
    Fetches key financial data for a given stock ticker, returning raw numbers.
    It uses yfinance first, then Yahoo quote endpoint/fast_info fallback.
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

        identity_fields = [
            data.get("Regular Market Price"),
            data.get("Market Cap"),
            data.get("Short Name"),
            data.get("Exchange"),
        ]
        if all(value is None for value in identity_fields):
            raise TickerNotFound(f"No data found for ticker '{ticker}'. It may be delisted or invalid.")

        core_metrics = [
            data.get("ROE"),
            data.get("ROA"),
            data.get("ROIC"),
            data.get("Debt to Equity Ratio"),
            data.get("Profit Margins"),
            data.get("Operating Margin"),
            data.get("FCF Margin"),
            data.get("Cash Conversion"),
            data.get("Interest Coverage"),
            data.get("P/E Ratio"),
            data.get("Dividend Yield"),
            data.get("P/B Ratio"),
            data.get("EPS"),
            data.get("Revenue Growth"),
            data.get("EPS Growth"),
            data.get("Quarterly Revenue Growth"),
            data.get("Quarterly EPS Growth"),
            data.get("Forward P/E"),
            data.get("PEG Ratio"),
            data.get("Operating Cash Flow"),
            data.get("Free Cash Flow"),
            data.get("Net Income"),
        ]
        if all(metric is None for metric in core_metrics):
            data["Data Quality Warning"] = "fundamental_metrics_sparse"

        try:
            financials = stock.financials
            if financials is not None and not financials.empty:
                if 'Total Revenue' in financials.index:
                    data['Historical Revenue'] = _series_to_recent_dict(financials.loc['Total Revenue'], limit=4)
                if 'Net Income' in financials.index:
                    data['Historical Net Income'] = _series_to_recent_dict(financials.loc['Net Income'], limit=4)
                    if data.get("Net Income") is None:
                        values = list(data['Historical Net Income'].values())
                        data["Net Income"] = values[0] if values else None
                if 'Free Cash Flow' in financials.index:
                    data['Historical FCF'] = _series_to_recent_dict(financials.loc['Free Cash Flow'], limit=4)
                elif 'Operating Cash Flow' in financials.index and 'Capital Expenditure' in financials.index:
                    data['Historical FCF'] = _series_to_recent_dict(
                        financials.loc['Operating Cash Flow'] + financials.loc['Capital Expenditure'],
                        limit=4,
                    )
                if 'Diluted EPS' in financials.index:
                    data['Historical EPS'] = _series_to_recent_dict(financials.loc['Diluted EPS'], limit=4)
                elif 'Basic EPS' in financials.index:
                    data['Historical EPS'] = _series_to_recent_dict(financials.loc['Basic EPS'], limit=4)
        except Exception as exc:
            print(f"Historical growth data fetch failed for {ticker}: {exc}")

        try:
            cashflow = stock.cashflow
            if cashflow is not None and not cashflow.empty:
                if 'Free Cash Flow' in cashflow.index:
                    data['Historical Free Cash Flow'] = _series_to_recent_dict(cashflow.loc['Free Cash Flow'], limit=4)
                if 'Operating Cash Flow' in cashflow.index:
                    data['Historical Operating Cash Flow'] = _series_to_recent_dict(cashflow.loc['Operating Cash Flow'], limit=4)
        except Exception as exc:
            print(f"Historical cash flow fetch failed for {ticker}: {exc}")

        try:
            quarterly = stock.quarterly_financials
            if quarterly is not None and not quarterly.empty:
                if 'Total Revenue' in quarterly.index:
                    data['Quarterly Revenue'] = _series_to_recent_dict(quarterly.loc['Total Revenue'], limit=5)
                if 'Net Income' in quarterly.index:
                    data['Quarterly Net Income'] = _series_to_recent_dict(quarterly.loc['Net Income'], limit=5)
                if 'Diluted EPS' in quarterly.index:
                    data['Quarterly EPS'] = _series_to_recent_dict(quarterly.loc['Diluted EPS'], limit=5)
                elif 'Basic EPS' in quarterly.index:
                    data['Quarterly EPS'] = _series_to_recent_dict(quarterly.loc['Basic EPS'], limit=5)
        except Exception as exc:
            print(f"Quarterly growth data fetch failed for {ticker}: {exc}")

        try:
            quarterly_cashflow = stock.quarterly_cashflow
            if quarterly_cashflow is not None and not quarterly_cashflow.empty:
                if 'Free Cash Flow' in quarterly_cashflow.index:
                    data['Quarterly Free Cash Flow'] = _series_to_recent_dict(quarterly_cashflow.loc['Free Cash Flow'], limit=5)
                if 'Operating Cash Flow' in quarterly_cashflow.index:
                    data['Quarterly Operating Cash Flow'] = _series_to_recent_dict(quarterly_cashflow.loc['Operating Cash Flow'], limit=5)
        except Exception as exc:
            print(f"Quarterly cash flow fetch failed for {ticker}: {exc}")

        if data.get("Cash Conversion") is None:
            data["Cash Conversion"] = _safe_ratio(data.get("Free Cash Flow"), data.get("Net Income"))

        cache_handler.save_to_cache(cache_key, data)
        return data

    except TickerNotFound as e:
        print(f"Data fetching failed for {ticker}: {e}")
        raise
    except Exception as e:
        print(f"An unexpected data fetch error occurred for {ticker}: {e}")
        raise TickerNotFound(f"An unexpected error occurred while fetching data for {ticker}: {e}")


if __name__ == '__main__':
    test_ticker = 'AAPL'
    financials = get_financial_data(test_ticker)

    if financials:
        print(f"Financial Data for {test_ticker}:")
        for key, value in financials.items():
            print(f"- {key}: {value} (type: {type(value).__name__})")
