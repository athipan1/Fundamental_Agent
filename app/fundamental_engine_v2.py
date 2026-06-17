from __future__ import annotations

from typing import Any, Dict, List, Optional


SECTOR_PEERS: Dict[str, List[str]] = {
    "Technology": ["MSFT", "AAPL", "NVDA", "ADBE", "CRM", "INTU", "ORCL"],
    "Communication Services": ["GOOGL", "META", "NFLX", "TMUS", "DIS"],
    "Energy": ["XOM", "CVX", "COP", "EOG", "APA", "SLB"],
    "Financial Services": ["JPM", "BAC", "WFC", "GS", "MS", "ACGL", "CB"],
    "Healthcare": ["LLY", "UNH", "JNJ", "MRK", "ABBV", "TMO", "ISRG"],
    "Consumer Cyclical": ["AMZN", "TSLA", "HD", "NKE", "LOW", "MCD"],
    "Consumer Defensive": ["WMT", "COST", "PG", "KO", "PEP"],
    "Industrials": ["CAT", "GE", "HON", "UPS", "RTX", "ADP"],
    "Real Estate": ["PLD", "AMT", "EQIX", "SPG", "O"],
    "Utilities": ["NEE", "DUK", "SO", "AEP", "EXC"],
    "Basic Materials": ["LIN", "SHW", "FCX", "NEM", "APD"],
}

SECTOR_RULES: Dict[str, Dict[str, float]] = {
    "Technology": {"quality": 0.30, "growth": 0.30, "valuation": 0.15, "financial_health": 0.10, "cash_flow": 0.15},
    "Communication Services": {"quality": 0.25, "growth": 0.25, "valuation": 0.20, "financial_health": 0.10, "cash_flow": 0.20},
    "Energy": {"quality": 0.20, "growth": 0.10, "valuation": 0.25, "financial_health": 0.15, "cash_flow": 0.30},
    "Financial Services": {"quality": 0.35, "growth": 0.10, "valuation": 0.20, "financial_health": 0.25, "cash_flow": 0.10},
    "Healthcare": {"quality": 0.25, "growth": 0.30, "valuation": 0.15, "financial_health": 0.15, "cash_flow": 0.15},
    "Real Estate": {"quality": 0.15, "growth": 0.10, "valuation": 0.25, "financial_health": 0.25, "cash_flow": 0.25},
    "Utilities": {"quality": 0.20, "growth": 0.10, "valuation": 0.20, "financial_health": 0.25, "cash_flow": 0.25},
    "default": {"quality": 0.25, "growth": 0.20, "valuation": 0.20, "financial_health": 0.15, "cash_flow": 0.20},
}


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def score_higher_better(value: Any, weak: float, strong: float) -> float:
    value = safe_float(value)
    if value is None:
        return 0.0
    if value <= weak:
        return 0.0
    if value >= strong:
        return 1.0
    return clamp((value - weak) / (strong - weak))


def score_lower_better(value: Any, strong: float, weak: float) -> float:
    value = safe_float(value)
    if value is None:
        return 0.0
    if value <= strong and value > 0:
        return 1.0
    if value >= weak or value <= 0:
        return 0.0
    return clamp((weak - value) / (weak - strong))


def weighted_average(parts: List[tuple[float, float]]) -> float:
    active = [(score, weight) for score, weight in parts if score > 0]
    if not active:
        return 0.0
    total_weight = sum(weight for _, weight in active)
    if total_weight <= 0:
        return 0.0
    return sum(score * weight for score, weight in active) / total_weight


def normalize_debt_to_equity(value: Any) -> Optional[float]:
    value = safe_float(value)
    if value is None:
        return None
    if value > 10:
        return value / 100.0
    return value


def score_reasonable_pe(pe: Any, sector: str) -> float:
    pe = safe_float(pe)
    if pe is None or pe <= 0:
        return 0.0
    if sector in {"Technology", "Healthcare", "Communication Services"}:
        if 10 <= pe <= 35:
            return 1.0
        if pe < 10:
            return 0.55
        if pe <= 60:
            return 0.45
        return 0.10
    if sector in {"Energy", "Financial Services", "Utilities", "Real Estate"}:
        if 5 <= pe <= 18:
            return 1.0
        if pe < 5:
            return 0.55
        if pe <= 30:
            return 0.45
        return 0.10
    if 8 <= pe <= 25:
        return 1.0
    if pe < 8:
        return 0.55
    if pe <= 40:
        return 0.45
    return 0.10


def _ordered_numeric_values(series_dict: Any) -> List[float]:
    if not isinstance(series_dict, dict):
        return []
    values: List[float] = []
    for key in sorted(series_dict.keys(), reverse=True):
        value = safe_float(series_dict.get(key))
        if value is not None:
            values.append(value)
    return values


def calculate_cagr_from_series(series_dict: Any, periods: Optional[int] = None) -> Optional[float]:
    values = _ordered_numeric_values(series_dict)
    if len(values) < 2:
        return None
    actual_periods = min(len(values) - 1, periods or len(values) - 1)
    newest = values[0]
    oldest = values[actual_periods]
    if oldest is None or newest is None or oldest <= 0 or actual_periods <= 0:
        return None
    try:
        return (newest / oldest) ** (1 / actual_periods) - 1
    except Exception:
        return None


def calculate_qoq_growth(series_dict: Any) -> Optional[float]:
    values = _ordered_numeric_values(series_dict)
    if len(values) < 2:
        return None
    newest, previous = values[0], values[1]
    if previous == 0:
        return None
    try:
        return (newest - previous) / abs(previous)
    except Exception:
        return None


def infer_sector(data: Dict[str, Any]) -> str:
    sector = data.get("Sector") or data.get("sector")
    if sector:
        return str(sector)
    short_name = str(data.get("Short Name") or "").lower()
    if any(word in short_name for word in ["bank", "financial", "insurance", "capital"]):
        return "Financial Services"
    if any(word in short_name for word in ["oil", "energy", "petroleum", "gas"]):
        return "Energy"
    if any(word in short_name for word in ["software", "semiconductor", "technology", "systems"]):
        return "Technology"
    return "default"


def peer_universe_for_sector(sector: str, ticker: str) -> List[str]:
    peers = list(SECTOR_PEERS.get(sector, []))
    if ticker not in peers:
        peers = [ticker] + peers
    return peers[:8]


def calculate_score_breakdown(ticker: str, data: Dict[str, Any], style: str = "growth") -> Dict[str, Any]:
    sector = infer_sector(data)
    weights = SECTOR_RULES.get(sector, SECTOR_RULES["default"])

    roe = safe_float(data.get("ROE"))
    roa = safe_float(data.get("ROA"))
    roic = safe_float(data.get("ROIC"))
    margins = safe_float(data.get("Profit Margins"))
    operating_margin = safe_float(data.get("Operating Margin"))
    gross_margin = safe_float(data.get("Gross Margin"))
    fcf_margin = safe_float(data.get("FCF Margin"))
    interest_coverage = safe_float(data.get("Interest Coverage"))
    eps = safe_float(data.get("EPS"))
    revenue_growth = safe_float(data.get("Revenue Growth"))
    eps_growth = safe_float(data.get("EPS Growth"))
    revenue_3y_cagr = calculate_cagr_from_series(data.get("Historical Revenue"), periods=3)
    fcf_3y_cagr = calculate_cagr_from_series(data.get("Historical Free Cash Flow"), periods=3)
    eps_3y_cagr = calculate_cagr_from_series(data.get("Historical Diluted EPS"), periods=3)
    qoq_revenue_growth = calculate_qoq_growth(data.get("Quarterly Revenue"))
    qoq_eps_growth = calculate_qoq_growth(data.get("Quarterly Diluted EPS"))
    qoq_fcf_growth = calculate_qoq_growth(data.get("Quarterly Free Cash Flow"))
    pe = safe_float(data.get("P/E Ratio"))
    forward_pe = safe_float(data.get("Forward P/E"))
    peg = safe_float(data.get("PEG Ratio"))
    pb = safe_float(data.get("P/B Ratio"))
    debt_to_equity = normalize_debt_to_equity(data.get("Debt to Equity Ratio"))
    cash_flow = safe_float(data.get("Operating Cash Flow"))
    free_cash_flow = safe_float(data.get("Free Cash Flow"))
    market_cap = safe_float(data.get("Market Cap"))
    net_cash = safe_float(data.get("Net Cash"))

    quality_score = round(weighted_average([
        (score_higher_better(roe, 0.04, 0.22), 0.20),
        (score_higher_better(roa, 0.02, 0.12), 0.12),
        (score_higher_better(roic, 0.04, 0.18), 0.16),
        (score_higher_better(margins, 0.02, 0.25), 0.14),
        (score_higher_better(operating_margin, 0.04, 0.25), 0.12),
        (score_higher_better(gross_margin, 0.15, 0.60), 0.08),
        (score_higher_better(fcf_margin, 0.02, 0.18), 0.08),
        (score_higher_better(interest_coverage, 2.0, 12.0), 0.06),
        (score_higher_better(eps, 0.0, 5.0), 0.02),
        (score_higher_better(market_cap, 1_000_000_000, 100_000_000_000), 0.02),
    ]), 4)

    growth_score = round(weighted_average([
        (score_higher_better(revenue_3y_cagr, 0.00, 0.22), 0.28),
        (score_higher_better(revenue_growth, 0.00, 0.25), 0.18),
        (score_higher_better(eps_3y_cagr, 0.00, 0.22), 0.16),
        (score_higher_better(eps_growth, 0.00, 0.25), 0.14),
        (score_higher_better(fcf_3y_cagr, 0.00, 0.25), 0.14),
        (score_higher_better(qoq_revenue_growth, -0.02, 0.10), 0.04),
        (score_higher_better(qoq_eps_growth, -0.02, 0.10), 0.03),
        (score_higher_better(qoq_fcf_growth, -0.02, 0.10), 0.03),
    ]), 4)

    valuation_score = round((
        score_reasonable_pe(pe, sector) * 0.35
        + score_reasonable_pe(forward_pe, sector) * 0.25
        + score_lower_better(peg, 0.4, 2.0) * 0.25
        + score_lower_better(pb, 0.7, 8.0) * 0.15
    ), 4)

    financial_health_score = round(weighted_average([
        (score_lower_better(debt_to_equity, 0.25, 2.5), 0.40),
        (score_higher_better(cash_flow, 0.0, 5_000_000_000), 0.20),
        (score_higher_better(free_cash_flow, 0.0, 5_000_000_000), 0.15),
        (score_higher_better(interest_coverage, 2.0, 12.0), 0.15),
        (score_higher_better(net_cash, 0.0, 10_000_000_000), 0.10),
    ]), 4)

    cash_flow_score = round(weighted_average([
        (score_higher_better(cash_flow, 0.0, 10_000_000_000), 0.40),
        (score_higher_better(free_cash_flow, 0.0, 10_000_000_000), 0.35),
        (score_higher_better(fcf_margin, 0.02, 0.18), 0.25),
    ]), 4)

    total_score = round(
        quality_score * weights["quality"]
        + growth_score * weights["growth"]
        + valuation_score * weights["valuation"]
        + financial_health_score * weights["financial_health"]
        + cash_flow_score * weights["cash_flow"],
        4,
    )

    risk_flags: List[str] = []
    if debt_to_equity is not None and debt_to_equity > 2.0:
        risk_flags.append("high_debt")
    if interest_coverage is not None and interest_coverage < 2.0:
        risk_flags.append("weak_interest_coverage")
    if cash_flow is not None and cash_flow < 0:
        risk_flags.append("negative_operating_cash_flow")
    if free_cash_flow is not None and free_cash_flow < 0:
        risk_flags.append("negative_free_cash_flow")
    if revenue_3y_cagr is not None and revenue_3y_cagr < 0:
        risk_flags.append("three_year_revenue_decline")
    if fcf_3y_cagr is not None and fcf_3y_cagr < 0:
        risk_flags.append("three_year_fcf_decline")
    if revenue_growth is not None and revenue_growth < 0:
        risk_flags.append("revenue_decline")
    if eps is not None and eps < 0:
        risk_flags.append("negative_eps")
    if pe is not None and pe > 60:
        risk_flags.append("very_high_pe")
    if data.get("Data Quality Warning"):
        risk_flags.append(str(data.get("Data Quality Warning")))

    peer_symbols = peer_universe_for_sector(sector, ticker)
    comparison = {
        "sector": sector,
        "peer_symbols": peer_symbols,
        "note": "Peer comparison v1 uses a sector peer universe for context; full peer metric medians require external financial data provider integration.",
        "relative_view": "above_watch_threshold" if total_score >= 0.6 else "needs_more_confirmation",
    }

    return {
        "quality_score": quality_score,
        "growth_score": growth_score,
        "valuation_score": valuation_score,
        "financial_health_score": financial_health_score,
        "cash_flow_score": cash_flow_score,
        "confidence_score": total_score,
        "sector": sector,
        "sector_weights": weights,
        "risk_flags": risk_flags,
        "comparative_analysis": comparison,
        "key_metrics": {
            "roe": roe,
            "roa": roa,
            "roic": roic,
            "profit_margins": margins,
            "operating_margin": operating_margin,
            "gross_margin": gross_margin,
            "fcf_margin": fcf_margin,
            "interest_coverage": interest_coverage,
            "eps": eps,
            "revenue_growth_ttm": revenue_growth,
            "eps_growth_ttm": eps_growth,
            "revenue_3y_cagr": revenue_3y_cagr,
            "eps_3y_cagr": eps_3y_cagr,
            "fcf_3y_cagr": fcf_3y_cagr,
            "qoq_revenue_growth": qoq_revenue_growth,
            "qoq_eps_growth": qoq_eps_growth,
            "qoq_fcf_growth": qoq_fcf_growth,
            "pe_ratio": pe,
            "forward_pe": forward_pe,
            "peg_ratio": peg,
            "pb_ratio": pb,
            "debt_to_equity": debt_to_equity,
            "operating_cash_flow": cash_flow,
            "free_cash_flow": free_cash_flow,
            "market_cap": market_cap,
            "net_cash": net_cash,
        },
    }


def action_from_score(score: float, risk_flags: List[str]) -> str:
    severe_flags = {"negative_operating_cash_flow", "negative_free_cash_flow", "negative_eps", "high_debt", "weak_interest_coverage"}
    severe_count = len(severe_flags.intersection(set(risk_flags or [])))
    if score >= 0.72 and severe_count == 0:
        return "buy"
    if score >= 0.55 and severe_count <= 1:
        return "neutral"
    if score < 0.30 or severe_count >= 2:
        return "sell"
    return "neutral"


def build_reason(ticker: str, breakdown: Dict[str, Any]) -> str:
    flags = breakdown.get("risk_flags") or []
    flag_text = ", ".join(flags) if flags else "ไม่พบธงความเสี่ยงหลัก"
    key_metrics = breakdown.get("key_metrics") or {}
    return (
        f"{ticker}: คะแนนพื้นฐานรวม {breakdown['confidence_score']:.2f} "
        f"โดยแยกเป็น Quality {breakdown['quality_score']:.2f}, Growth {breakdown['growth_score']:.2f}, "
        f"Valuation {breakdown['valuation_score']:.2f}, Financial Health {breakdown['financial_health_score']:.2f}, "
        f"Cash Flow {breakdown['cash_flow_score']:.2f}. "
        f"Growth drivers: Revenue 3Y CAGR={key_metrics.get('revenue_3y_cagr')}, "
        f"EPS 3Y CAGR={key_metrics.get('eps_3y_cagr')}, FCF 3Y CAGR={key_metrics.get('fcf_3y_cagr')}. "
        f"Sector={breakdown['sector']}. Risk flags: {flag_text}."
    )


def run_fundamental_v2(ticker: str, data: Dict[str, Any], style: str = "growth") -> Dict[str, Any]:
    breakdown = calculate_score_breakdown(ticker, data, style=style)
    action = action_from_score(breakdown["confidence_score"], breakdown.get("risk_flags", []))
    reason = build_reason(ticker, breakdown)
    return {
        "strength": action,
        "score": breakdown["confidence_score"],
        "reasoning": reason,
        "analysis_source": "fundamental_engine_v2",
        "score_details": {
            "quality_score": breakdown["quality_score"],
            "growth_score": breakdown["growth_score"],
            "valuation_score": breakdown["valuation_score"],
            "financial_health_score": breakdown["financial_health_score"],
            "cash_flow_score": breakdown["cash_flow_score"],
        },
        "risk_flags": breakdown["risk_flags"],
        "sector": breakdown["sector"],
        "comparative_analysis": breakdown["comparative_analysis"],
        "key_metrics": breakdown["key_metrics"],
        "sector_weights": breakdown["sector_weights"],
    }
