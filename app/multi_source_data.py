from __future__ import annotations

from typing import Any, Dict

from .data_fetcher import get_financial_data as get_yahoo_financial_data
from .evidence_reconciler import reconcile_financial_sources
from .sec_data_provider import fetch_sec_financial_data


def get_financial_data(ticker: str) -> Dict[str, Any]:
    """Return Yahoo market data enriched with SEC filing evidence."""
    yahoo_data = get_yahoo_financial_data(ticker)
    sec_data = fetch_sec_financial_data(ticker)
    return reconcile_financial_sources(yahoo_data, sec_data)
