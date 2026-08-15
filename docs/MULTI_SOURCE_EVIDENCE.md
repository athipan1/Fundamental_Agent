# Multi-source fundamental evidence

Fundamental_Agent enriches Yahoo/yfinance market and valuation data with filing-derived financial history from the SEC EDGAR Company Facts API for supported U.S. issuers.

## Data flow

1. `data_fetcher.py` collects the existing Yahoo/yfinance market, ratio, annual and quarterly data.
2. `sec_data_provider.py` resolves ticker to CIK and fetches SEC XBRL Company Facts.
3. SEC facts are normalized into annual and quarterly revenue, net income, EPS, operating cash flow and capital expenditure histories. Only expected XBRL units are accepted, so an unexpected currency or dimension is treated as missing evidence rather than guessed.
4. Free cash flow is derived as operating cash flow minus capital expenditure when both filing facts exist for the same period.
5. `evidence_reconciler.py` compares matching Yahoo and SEC statement periods.
6. SEC filing history wins for matching statement periods while Yahoo remains the source for market/valuation fields.
7. The deterministic Fundamental Engine V2 scores the reconciled dataset.
8. `evidence_safety.py` applies a fail-closed evidence-conflict gate before the result is cached or returned.

The API remains advisory. Strategy bucket authority stays with Manager_Agent.

## Reconciliation states

- `multi_source_verified`: usable SEC evidence was merged and no matching period exceeded the divergence threshold.
- `multi_source_divergent`: at least one matching statement period exceeded the divergence threshold.
- `single_source_yahoo`: SEC was disabled, not applicable, unavailable, or returned no usable filing evidence.

Operational provenance is exposed under `comparative_analysis.data_provenance`, including provider names, SEC CIK, SEC status, filing fields used and divergence fields.

## Evidence-conflict safety gate

A material disagreement between independent data sources must not become a bullish trading input by accident. When reconciliation returns `multi_source_divergent`:

- `buy` or `strong_buy` is downgraded to `neutral` so the API returns HOLD.
- the raw analysis confidence is capped at `0.30`.
- `cross_source_divergence` and `evidence_conflict_review_required` are added to risk flags.
- the reasoning explicitly requires Manager review before trading.
- SELL is not promoted to HOLD, so a defensive signal remains defensive.

This gate is deliberately asymmetric: uncertain evidence can block risk-taking, but it cannot make a negative decision more aggressive or invent a positive decision.

## Configuration

- `FUNDAMENTAL_SEC_ENABLED=true` enables SEC enrichment. Default: `true`.
- `SEC_USER_AGENT` declares the automated client to SEC. Set this to an application/company name plus a monitored contact email for production.
- `SEC_REQUEST_TIMEOUT_SECONDS=6` controls the HTTP timeout and is clamped to 1-30 seconds.
- `SEC_MIN_REQUEST_INTERVAL_SECONDS=0.12` applies an in-process request throttle and is clamped to at least 0.10 seconds.
- `FUNDAMENTAL_SOURCE_DIVERGENCE_TOLERANCE=0.20` controls the relative-difference threshold used to flag cross-source disagreement.

The SEC provider is best-effort and never raises a SEC network failure into the trading path. A failure keeps Yahoo data available and records `sec_source_unavailable` so evidence quality remains visible.

## Cache rollout

The final-analysis cache namespace is `fundamental-multisource-v1`. This intentionally invalidates pre-upgrade Yahoo-only analysis cache entries after deployment so the first post-upgrade analysis goes through the multi-source evidence pipeline.

## SEC access policy

The implementation sends a declared `User-Agent`, throttles requests, accepts only expected XBRL units, fetches only the ticker mapping and the requested issuer's Company Facts payload, and does not crawl filing pages.
