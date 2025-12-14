from typing import Optional
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure the Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('models/gemini-flash-latest')


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

    # Sort by year (descending) to get the last 4 years
    years = sorted(historical_revenue.keys(), reverse=True)[:4]
    revenues = [historical_revenue[year] for year in years]

    # Check growth for the last 3 periods
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


def calculate_cagr(historical_revenue: dict) -> Optional[float]:
    """Calculates the 3-year Compound Annual Growth Rate (CAGR)."""
    if not historical_revenue or len(historical_revenue) < 4:
        return None

    years = sorted(historical_revenue.keys(), reverse=True)[:4]
    start_value = historical_revenue[years[3]]  # Earliest year
    end_value = historical_revenue[years[0]]   # Most recent year

    if start_value is None or end_value is None or start_value <= 0:
        return None

    try:
        cagr = ((end_value / start_value) ** (1/3)) - 1
        return cagr
    except (TypeError, ZeroDivisionError):
        return None


def get_margins_score(margins):
    """Calculates the score component for profit margins."""
    if margins > 0.20:
        return 0.10
    return 0.0


def get_pe_ratio_score(pe_ratio):
    """Calculates the score component for P/E ratio."""
    if pe_ratio is None:
        return 0.0
    if 0 < pe_ratio < 15:
        return 0.10
    if pe_ratio < 25:
        return 0.05
    return 0.0


def get_dividend_yield_score(dividend_yield):
    """Calculates the score component for dividend yield."""
    if dividend_yield is None:
        return 0.0
    if dividend_yield > 0.04:
        return 0.10
    if dividend_yield > 0.02:
        return 0.05
    return 0.0


def get_pb_ratio_score(pb_ratio):
    """Calculates the score component for P/B ratio."""
    if pb_ratio is None:
        return 0.0
    if 0 < pb_ratio < 1.2:
        return 0.05
    return 0.0


def get_eps_score(eps):
    """Calculates the score component for EPS."""
    if eps is None:
        return 0.0
    if eps > 0:
        return 0.05
    return 0.0


def get_growth_score(growth_rate):
    """Gives a significant score for high growth rates (for Revenue and EPS)."""
    if growth_rate is None:
        return 0.0
    if growth_rate > 0.25:
        return 0.20  # High score for strong growth
    if growth_rate > 0.10:
        return 0.10
    if growth_rate > 0:
        return 0.05
    return 0.0


def get_forward_pe_score(forward_pe):
    """Scores based on the forward P/E ratio."""
    if forward_pe is None:
        return 0.0
    if 0 < forward_pe < 15:
        return 0.10
    if forward_pe < 25:
        return 0.05
    return 0.0


def get_peg_ratio_score(peg_ratio):
    """Scores based on the PEG ratio. Lower is better."""
    if peg_ratio is None:
        return 0.0
    if 0 < peg_ratio < 1.0:
        return 0.10  # Very favorable
    if peg_ratio < 1.5:
        return 0.05
    return 0.0


def get_cash_flow_score(cash_flow):
    """Scores based on operating cash flow. Positive is good."""
    if cash_flow is None:
        return 0.0
    if cash_flow > 0:
        return 0.10  # Positive cash flow is crucial
    return 0.0


def calculate_score(data: dict, trend_score: float) -> float:
    """Calculates a score from 0.0 to 1.0 based on raw financial metrics."""
    try:
        roe = data.get("ROE") or 0.0
        de_ratio = (data.get("Debt to Equity Ratio") or float('inf')) / 100.0
        margins = data.get("Profit Margins") or 0.0
        pe_ratio = data.get("P/E Ratio")
        dividend_yield = data.get("Dividend Yield")
        pb_ratio = data.get("P/B Ratio")
        eps = data.get("EPS")

        # Growth Investing Focus
        revenue_growth = data.get("Revenue Growth")
        eps_growth = data.get("EPS Growth")
        forward_pe = data.get("Forward P/E")
        peg_ratio = data.get("PEG Ratio")
        cash_flow = data.get("Operating Cash Flow")

        score = 0.0
        # Growth Factors (High Weight)
        score += get_growth_score(revenue_growth)
        score += get_growth_score(eps_growth)
        score += trend_score  # Historical growth consistency

        # Valuation Factors
        score += get_peg_ratio_score(peg_ratio)
        score += get_forward_pe_score(forward_pe)
        score += get_pe_ratio_score(pe_ratio)
        score += get_pb_ratio_score(pb_ratio)

        # Quality & Stability Factors
        score += get_roe_score(roe)
        score += get_de_ratio_score(de_ratio)
        score += get_margins_score(margins)
        score += get_cash_flow_score(cash_flow)
        score += get_eps_score(eps)

        # Lower weight for dividends in a growth model
        score += get_dividend_yield_score(dividend_yield) * 0.5

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
    data: dict, ticker: str, trend: str, cagr: Optional[float]
) -> str:
    """Creates an advanced Chain-of-Thought prompt for the Gemini model."""
    # Helper for safe formatting
    def format_value(value, format_spec):
        return f"{value:{format_spec}}" if isinstance(value, (int, float)) else "N/A"

    formatted_data = {
        # Growth
        "Revenue Growth (YoY)": format_value(data.get('Revenue Growth'), '.2%'),
        "EPS Growth (YoY)": format_value(data.get('EPS Growth'), '.2%'),
        "3-Year Revenue Trend": trend,
        "3-Year Revenue CAGR": format_value(cagr, '.2%'),
        "Operating Cash Flow": f"${data.get('Operating Cash Flow', 0):,.0f}",

        # Valuation
        "Forward P/E Ratio": format_value(data.get('Forward P/E'), '.2f'),
        "PEG Ratio": format_value(data.get('PEG Ratio'), '.2f'),
        "P/E Ratio": format_value(data.get('P/E Ratio'), '.2f'),
        "P/B Ratio": format_value(data.get('P/B Ratio'), '.2f'),

        # Quality & Health
        "Return on Equity (ROE)": format_value(data.get('ROE'), '.2%'),
        "Debt to Equity Ratio": format_value(data.get('Debt to Equity Ratio'), '.2f'),
        "Profit Margins": format_value(data.get('Profit Margins'), '.2%'),
        "Earnings Per Share (EPS)": format_value(data.get('EPS'), '.2f'),
        "Dividend Yield": format_value(data.get('Dividend Yield'), '.2%'),
    }

    data_string = "\n".join([f"- {key}: {value}" for key, value in formatted_data.items()])
    prompt = (
        f"คุณคือผู้เชี่ยวชาญด้านการวิเคราะห์หุ้นเติบโต (Growth Investing)\n"
        f"**คำสั่ง:** วิเคราะห์ข้อมูลทางการเงินของบริษัท {ticker} และสรุปภาพรวมในรูปแบบย่อหน้าเดียวที่คมชัดและลึกซึ้ง\n"
        f"**ข้อมูลที่มี:**\n{data_string}\n\n"
        f"**กฎเหล็ก (Guardrails):**\n"
        f"1.  **ห้าม** สร้างข้อมูลหรือตัวเลขใดๆ ที่ไม่มีอยู่ใน `ข้อมูลที่มี` โดยเด็ดขาด\n"
        f"2.  วิเคราะห์จากข้อมูลที่ให้มาเท่านั้น\n"
        f"3.  หากข้อมูลบางอย่างเป็น 'N/A' ให้ระบุว่า \"ข้อมูลไม่เพียงพอที่จะประเมิน\" ในส่วนนั้นๆ\n"
        f"4.  คำตอบทั้งหมดต้องเป็นภาษาไทย\n\n"
        f"**กระบวนการคิด (Chain of Thought) สำหรับหุ้นเติบโต:**\n"
        f"1.  **ประเมินศักยภาพการเติบโต (Growth Potential):** นี่คือส่วนสำคัญที่สุด "
        f"ดูที่ Revenue Growth และ EPS Growth เป็นหลัก ว่าเติบโตสูงและน่าประทับใจหรือไม่ "
        f"ใช้ 3-Year Trend และ CAGR เพื่อดูความสม่ำเสมอของการเติบโตในอดีต\n"
        f"2.  **ประเมินมูลค่าเทียบกับการเติบโต (Valuation vs. Growth):** หุ้นเติบโตมักมี P/E สูง "
        f"ดังนั้นให้ดูที่ Forward P/E เพื่อประเมินมูลค่าในอนาคต และใช้ PEG Ratio เพื่อตัดสินว่า P/E "
        f"สูงนั้นสมเหตุสมผลหรือไม่ (ค่า PEG ต่ำกว่า 1.5 ถือว่าดี)\n"
        f"3.  **ประเมินคุณภาพและเสถียรภาพ (Quality & Stability):** บริษัทเติบโตต้องมีพื้นฐานที่ดีด้วย "
        f"ดูที่ ROE และ Profit Margins เพื่อวัดความสามารถในการทำกำไร, "
        f"Operating Cash Flow เพื่อดูสภาพคล่องที่แท้จริง, และ Debt to Equity "
        f"เพื่อดูภาระหนี้สิน\n"
        f"4.  **สรุปภาพรวม:** สังเคราะห์ข้อมูลทั้งหมดเพื่อสร้างบทสรุปที่กระชับ "
        f"โดยเน้นที่ \"โอกาสในการเติบโต\" เทียบกับ \"ความเสี่ยงและมูลค่าปัจจุบัน\"\n\n"
        f"**ผลลัพธ์ที่ต้องการ:**\nเขียนบทวิเคราะห์สรุป (ย่อหน้าเดียว) ตามกระบวนการคิดข้างต้น"
    )
    return prompt


def analyze_financials(ticker: str, data: dict) -> dict:
    """
    Uses Python for scoring and JSON assembly, and an LLM for reasoning.
    """
    if not data:
        return None

    historical_revenue = data.get("Historical Revenue", {})
    trend_score, trend_string = get_revenue_trend_score(historical_revenue)
    cagr = calculate_cagr(historical_revenue)

    score = calculate_score(data, trend_score)
    strength = generate_strength(score)

    prompt = create_prompt(data, ticker, trend_string, cagr)

    reasoning = "ไม่สามารถสร้างคำวิเคราะห์ได้"  # Default value
    try:
        response = model.generate_content(prompt)
        generated_text = response.text.strip()
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
        'Quarterly Revenue Growth (yoy)': 0.079, 'Profit Margins': 0.2692
    }
    print(f"--- Starting analysis for {sample_ticker} ---")
    analysis_result = analyze_financials(sample_ticker, sample_data)
    if analysis_result:
        print("\n--- Analysis Result ---")
        print(json.dumps(analysis_result, indent=4, ensure_ascii=False))
