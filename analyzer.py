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
        return 0.30  # Adjusted weight
    if roe > 0.15:
        return 0.20  # Adjusted weight
    if roe > 0.05:
        return 0.10  # Adjusted weight
    return 0.0


def get_de_ratio_score(de_ratio):
    """Calculates the score component for D/E ratio."""
    if de_ratio < 0.5:
        return 0.25  # Adjusted weight
    if de_ratio < 1.0:
        return 0.15  # Adjusted weight
    if de_ratio < 2.0:
        return 0.05  # Adjusted weight
    return 0.0


def get_rev_growth_score(rev_growth):
    """Calculates the score component for revenue growth."""
    if rev_growth > 0.10:
        return 0.15  # Adjusted weight
    if rev_growth > 0.05:
        return 0.10  # Adjusted weight
    return 0.0


def get_margins_score(margins):
    """Calculates the score component for profit margins."""
    if margins > 0.20:
        return 0.10  # Adjusted weight
    return 0.0


def get_pe_ratio_score(pe_ratio):
    """Calculates the score component for P/E ratio."""
    if pe_ratio is None:
        return 0.0
    if pe_ratio < 15:
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


def calculate_score(data: dict) -> float:
    """Calculates a score from 0.0 to 1.0 based on raw financial metrics."""
    try:
        roe = data.get("ROE") or 0.0
        de_ratio = (data.get("Debt to Equity Ratio") or float('inf')) / 100.0
        rev_growth = data.get("Quarterly Revenue Growth (yoy)") or 0.0
        margins = data.get("Profit Margins") or 0.0
        pe_ratio = data.get("P/E Ratio")
        dividend_yield = data.get("Dividend Yield")

        score = 0.0
        score += get_roe_score(roe)
        score += get_de_ratio_score(de_ratio)
        score += get_rev_growth_score(rev_growth)
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


def create_prompt(data: dict, ticker: str) -> str:
    """Creates a simple prompt with formatted data for the LLM."""
    formatted_data = {
        "ROE": f"{data.get('ROE', 0):.2%}",
        "D/E Ratio": f"{data.get('Debt to Equity Ratio', 0):.2f}",
        "Rev Growth (yoy)":
            f"{data.get('Quarterly Revenue Growth (yoy)', 0):.2%}",
        "Profit Margins": f"{data.get('Profit Margins', 0):.2%}",
        "P/E Ratio": f"{data.get('P/E Ratio', 0):.2f}",
        "Dividend Yield": f"{data.get('Dividend Yield', 0):.2%}",
    }
    data_string = ", ".join([
        f"{key}: {value}" for key, value in formatted_data.items()
    ])

    prompt = f"""
    Based on the following data for {ticker} ({data_string}), write a single,
    brief sentence in Thai summarizing the financial situation.
    """
    return prompt


def analyze_financials(ticker: str, data: dict) -> dict:
    """
    Uses Python for scoring and JSON assembly, and an LLM for reasoning.
    """
    if not data:
        return None

    score = calculate_score(data)
    strength = generate_strength(score)

    prompt = create_prompt(data, ticker)
    messages = [{"role": "user", "content": prompt}]

    reasoning = "ไม่สามารถสร้างคำวิเคราะห์ได้"  # Default value
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
        'Quarterly Revenue Growth (yoy)': 0.079, 'Profit Margins': 0.2692
    }
    print(f"--- Starting analysis for {sample_ticker} ---")
    analysis_result = analyze_financials(sample_ticker, sample_data)
    if analysis_result:
        print("\n--- Analysis Result ---")
        print(json.dumps(analysis_result, indent=4, ensure_ascii=False))
