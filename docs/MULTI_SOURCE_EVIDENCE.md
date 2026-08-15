# Multi-source fundamental evidence

Fundamental_Agent now enriches Yahoo/yfinance market and valuation data with filing-derived financial history from the SEC EDGAR Company Facts API for supported U.S. issuers.

## Data flow

1. `data_fetcher.py` collects the existing Yahoo/yfinance market, ratio, annual and quarterly data.
2. `sec_data_provider.py` resolves ticker to CIK and fetches SEC XBRL Company Facts.
3. SEC facts are normalized into annual and quarterly revenue, net income, EPS, operating cash flow and capital expenditure histories. Free cash flow is derived as operating cash flow minus capital expenditure when both filing facts exist for the same period.
4. `evidence_reconciler.py` compares matching Yahoo and SEC statement periods.
5. SEC filing history wins for matching statement periods while Yahoo remains the source for market/valuation fields.
6. Material disagreement is surfaced as `cross_source_divergence` instead of being silently overwritten.
7. The deterministic Fundamental Engine V2 scores the reconciled dataset.

The API remains advisory. Strategy bucket authority stays with Manager_Agent.

## Reconciliation states

- `multi_source_verified`: SEC evidence was available and no matching period exceeded the divergence threshold.
- `multi_source_divergent`: at least one matching statement period exceeded the divergence threshold.
- `single_source_yahoo`: SEC was disabled, not applicable, unavailable, or returned no usable filing evidence.

Operational provenance is exposed under `comparative_analysis.data_provenance`, including provider names, SEC CIK, SEC status, filing fields used and divergence fields.

## Configuration

- `FUNDAMENTAL_SEC_ENABLED=true` enables SEC enrichment. Default: `true`.
- `SEC_USER_AGENT` declares the automated client to SEC. Set this to an application/company name plus a monitored contact email for production.
- `SEC_REQUEST_TIMEOUT_SECONDS=6` controls the HTTP timeout and is clamped to 1-30 seconds.
- `SEC_MIN_REQUEST_INTERVAL_SECONDS=0.12` applies an in-process request throttle and is clamped to at least 0.10 seconds.
- `FUNDAMENTAL_SOURCE_DIVERGENCE_TOLERANCE=0.20` controls the relative-difference threshold used to flag cross-source disagreement.

The SEC provider is best-effort and never raises a SEC network failure into the trading path. A failure keeps Yahoo data available and records `sec_source_unavailable` so confidence/data-quality policy can react to degraded evidence.

## SEC access policy

The implementation sends a declared `User-Agent`, throttles requests, fetches only ticker mapping and the requested issuer's Company Facts payload, and does not crawl filing pages.
