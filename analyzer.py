import torch
from transformers import pipeline
import json


# Using a more lightweight model to prevent memory-related crashes.
generator = pipeline(
    "text-generation",
    model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    model_kwargs={"torch_dtype": torch.bfloat16},
    device_map="auto",
)


def get_roe_score(roe):
    """Calculates the score component for ROE."""
    if roe > 0.20:
        return 0.25
    if roe > 0.15:
        return 0.15
    if roe > 0.05:
        return 0.05
    return 0.0


def get_de_ratio_score(de_ratio):
    """Calculates the score component for D/E ratio."""
    if de_ratio < 0.5:
        return 0.20
    if de_ratio < 1.0:
        return 0.10
    if de_ratio < 2.0:
        return 0.05
    return 0.0


def get_revenue_trend_score(historical_revenue: dict) -> tuple[float, str]:
    """
    Analyzes the 3-year revenue trend for growth consistency.
    Returns a score and a descriptive string.
    """
    if not historical_revenue or len(historical_revenue) < 4:
        return 0.0, "ข้อมูลไม่เพียงพอ"

    years = sorted(historical_revenue.keys(), reverse=True)[:4]
    revenues = [historical_revenue[year] for year in years]

    growth_years = 0
    if revenues[0] > revenues[1]:
        growth_years += 1
    if revenues[1] > revenues[2]:
        growth_years += 1
    if revenues[2] > revenues[3]:
        growth_years += 1

    if growth_years == 3:
        score = 0.15
        trend_string = "เติบโตต่อเนื่อง 3 ปี"
    elif growth_years == 2:
        score = 0.10
        trend_string = "เติบโต 2 ใน 3 ปีล่าสุด"
    elif growth_years == 1:
        score = 0.05
        trend_string = "เติบโต 1 ใน 3 ปีล่าสุด"
    else:
        score = 0.0
        trend_string = "รายได้ไม่เติบโต"

    return score, trend_string


def get_net_income_trend_score(
    historical_net_income: dict
) -> tuple[float, str]:
    """Analyzes the 3-year net income trend for growth consistency."""
    if not historical_net_income or len(historical_net_income) < 4:
        return 0.0, "ข้อมูลไม่เพียงพอ"

    years = sorted(historical_net_income.keys(), reverse=True)[:4]
    incomes = [historical_net_income[year] for year in years]

    growth_years = 0
    if incomes[0] > incomes[1]:
        growth_years += 1
    if incomes[1] > incomes[2]:
        growth_years += 1
    if incomes[2] > incomes[3]:
        growth_years += 1

    if growth_years == 3:
        score = 0.15
        trend_string = "เติบโตต่อเนื่อง 3 ปี"
    elif growth_years == 2:
        score = 0.10
        trend_string = "เติบโต 2 ใน 3 ปีล่าสุด"
    else:
        score = 0.0
        trend_string = "กำไรไม่สม่ำเสมอ"

    return score, trend_string


def get_debt_trend_score(historical_debt: dict) -> tuple[float, str]:
    """Analyzes the 3-year total debt trend."""
    if not historical_debt or len(historical_debt) < 4:
        return 0.0, "ข้อมูลไม่เพียงพอ"

    years = sorted(historical_debt.keys(), reverse=True)[:4]
    debts = [historical_debt[year] for year in years]

    increase_years = 0
    if debts[0] > debts[1]:
        increase_years += 1
    if debts[1] > debts[2]:
        increase_years += 1
    if debts[2] > debts[3]:
        increase_years += 1

    if increase_years == 0:
        score = 0.10
        trend_string = "หนี้สินลดลงหรือคงที่"
    elif increase_years <= 2:
        score = 0.0
        trend_string = "หนี้สินเพิ่มขึ้น"
    else:
        score = 0.0
        trend_string = "หนี้สินเพิ่มขึ้นทุกปี"

    return score, trend_string


def calculate_cagr(historical_revenue: dict) -> float | None:
    """Calculates the 3-year Compound Annual Growth Rate (CAGR)."""
    if not historical_revenue or len(historical_revenue) < 4:
        return None

    years = sorted(historical_revenue.keys(), reverse=True)[:4]
    start_value = historical_revenue[years[3]]
    end_value = historical_revenue[years[0]]

    if start_value is None or end_value is None or start_value <= 0:
        return None

    try:
        cagr = ((end_value / start_value) ** (1/3)) - 1
        return cagr
    except (TypeError, ZeroDivisionError):
        return None


def get_margins_score(margins):
    """Calculates the score component for profit margins."""
    if margins > 0.15:
        return 0.05
    return 0.0


def get_pe_ratio_score(pe_ratio):
    """Calculates the score component for P/E ratio."""
    if pe_ratio is None:
        return 0.0
    if pe_ratio < 20:
        return 0.05
    return 0.0


def get_dividend_yield_score(dividend_yield):
    """Calculates the score component for dividend yield."""
    if dividend_yield is None:
        return 0.0
    if dividend_yield > 0.03:
        return 0.05
    return 0.0


def calculate_score(
    data: dict,
    revenue_trend_score: float,
    net_income_trend_score: float,
    debt_trend_score: float,
) -> float:
    """Calculates a score from 0.0 to 1.0 based on raw financial metrics."""
    try:
        roe = data.get("ROE") or 0.0
        de_ratio = (data.get("Debt to Equity Ratio") or float('inf')) / 100.0
        margins = data.get("Profit Margins") or 0.0
        pe_ratio = data.get("P/E Ratio")
        dividend_yield = data.get("Dividend Yield")

        score = 0.0
        score += get_roe_score(roe)
        score += get_de_ratio_score(de_ratio)
        score += revenue_trend_score
        score += net_income_trend_score
        score += debt_trend_score
        score += get_margins_score(margins)
        score += get_pe_ratio_score(pe_ratio)
        score += get_dividend_yield_score(dividend_yield)

    except (ValueError, TypeError):
        return 0.0
    return min(round(score, 2), 1.0)


def generate_strength(score: float) -> str:
    """Generates a Thai strength summary based on the calculated score."""
    if score >= 0.7:
        return "พื้นฐานแข็งแกร่ง"
    if score >= 0.4:
        return "พื้นฐานปานกลาง"
    return "พื้นฐานอ่อนแอและมีความเสี่ยง"


def create_prompt(
    data: dict,
    ticker: str,
    revenue_trend: str,
    net_income_trend: str,
    debt_trend: str,
    cagr: float | None,
) -> str:
    """Creates a detailed prompt for the LLM."""
    formatted_data = {
        "ROE": f"{data.get('ROE', 0):.2%}",
        "D/E Ratio": f"{data.get('Debt to Equity Ratio', 0):.2f}",
        "Profit Margins": f"{data.get('Profit Margins', 0):.2%}",
        "P/E Ratio": f"{data.get('P/E Ratio', 0):.2f}",
        "Dividend Yield": f"{data.get('Dividend Yield', 0):.2%}",
        "Revenue Trend": revenue_trend,
        "Net Income Trend": net_income_trend,
        "Debt Trend": debt_trend,
    }
    if cagr is not None:
        formatted_data["3Y Revenue CAGR"] = f"{cagr:.2%}"

    data_string = ", ".join([
        f"{key}: {value}" for key, value in formatted_data.items()
    ])

    prompt = f"""
    วิเคราะห์สถานการณ์ทางการเงินของ {ticker} จากข้อมูลต่อไปนี้: {data_string}.
    สรุปเป็นประโยคสั้นๆ ไม่เกิน 20 คำเป็นภาษาไทย.
    """
    return prompt


def analyze_financials(ticker: str, data: dict) -> dict:
    """
    Uses Python for scoring and JSON assembly, and an LLM for reasoning.
    """
    if not data:
        return None

    historical_revenue = data.get("Historical Revenue", {})
    revenue_trend_score, revenue_trend_str = get_revenue_trend_score(
        historical_revenue
    )
    cagr = calculate_cagr(historical_revenue)

    historical_net_income = data.get("Historical Net Income", {})
    net_income_trend_score, net_income_trend_str = get_net_income_trend_score(
        historical_net_income
    )

    historical_debt = data.get("Historical Total Debt", {})
    debt_trend_score, debt_trend_str = get_debt_trend_score(historical_debt)

    score = calculate_score(
        data,
        revenue_trend_score,
        net_income_trend_score,
        debt_trend_score,
    )
    strength = generate_strength(score)

    prompt = create_prompt(
        data,
        ticker,
        revenue_trend_str,
        net_income_trend_str,
        debt_trend_str,
        cagr,
    )
    messages = [{"role": "user", "content": prompt}]

    reasoning = "ไม่สามารถสร้างคำวิเคราะห์ได้"
    try:
        outputs = generator(messages, max_new_tokens=128, do_sample=False)
        generated_text = outputs[0]["generated_text"][-1]['content'].strip()
        if generated_text:
            reasoning = generated_text
    except Exception as e:
        print(f"An error occurred during text generation: {e}")
        reasoning = f"เกิดข้อผิดพลาดในการสร้างคำวิเคราะห์: {e}"

    return {
        "strength": strength,
        "reasoning": reasoning,
        "score": score
    }


if __name__ == '__main__':
    sample_ticker = 'AAPL'
    sample_data = {
        'ROE': 1.7142, 'Debt to Equity Ratio': 152.41,
        'Profit Margins': 0.2692, 'P/E Ratio': 37.47, 'Dividend Yield': 0.37,
        'Historical Revenue': {
            '2023-09-30': 383285000000, '2022-09-30': 394328000000,
            '2021-09-30': 365817000000, '2020-09-30': 274515000000
        },
        'Historical Net Income': {
            '2023-09-30': 96995000000, '2022-09-30': 99803000000,
            '2021-09-30': 94680000000, '2020-09-30': 57411000000
        },
        'Historical Total Debt': {
            '2023-09-30': 111088000000, '2022-09-30': 120069000000,
            '2021-09-30': 124719000000, '2020-09-30': 112436000000
        }
    }
    analysis_result = analyze_financials(sample_ticker, sample_data)
    if analysis_result:
        print(json.dumps(analysis_result, indent=4, ensure_ascii=False))
