# Fundamental Evidence Contract

Fundamental_Agent publishes normalized financial evidence for Scanner_Agent and Manager_Agent.

It does **not** assign a strategy bucket. Manager_Agent remains the final classification authority.

## Version

```text
fundamental-evidence-v1
```

## Response fields

Every `FundamentalAnalysisData` response includes:

- `fundamental_score`
- `raw_scores`
- `fundamental_evidence`
- `evidence_version`
- `evidence_status`
- `evidence_completeness_score`
- `manager_decision_required=true`
- `bucket_decision_authority=manager`

## Evidence payload

`fundamental_evidence` contains:

- normalized five-dimension scores
- normalized financial metrics
- available and missing fields
- missing critical metrics
- evidence completeness
- evidence reasons
- risk flags
- data provenance
- `strategy_bucket_hint=null`

## Normalized scores

The evidence contract exports these fields in the `0.0–1.0` range:

- `quality_score`
- `growth_score`
- `valuation_score`
- `financial_health_score`
- `cash_flow_score`
- `fundamental_score`

## Financial metrics

The contract preserves metrics used by Scanner and Manager, including:

- ROE, ROA and ROIC
- profit, operating, gross and FCF margins
- cash conversion and interest coverage
- revenue, EPS and FCF growth
- three-year CAGR and quarter-over-quarter growth
- PE, forward PE, PEG and PB
- EV/EBITDA, price-to-sales and price-to-FCF
- FCF yield
- debt-to-equity
- operating and free cash flow
- net income, market cap and net cash
- dividend yield, dividend rate and payout ratio when available

Percentage-style dividend yield values are normalized to decimal form. For example, `3.5` becomes `0.035`.

Debt-to-equity values returned as percentages are also normalized. For example, `50` becomes `0.5`.

## Evidence status

```text
complete     completeness >= 0.80 and no critical metric is missing
partial      completeness >= 0.45
insufficient completeness < 0.45
```

Missing data is reported explicitly. Fundamental_Agent does not invent replacement metrics or force a bucket classification.

## Provenance

The response records the actual analysis path, such as:

- `fundamental_engine_v2`
- `fundamental_engine_v2_with_llm`
- scanner-prefetched analysis
- rule-based fallback

The analysis cache key includes the evidence contract version so stale cached results without evidence are not reused.

## System flow

```text
Fundamental evidence
  -> Scanner non-binding bucket hints
  -> Manager final classification
  -> Risk approval
  -> Execution validation
  -> Database persistence
```
