# Fundamental_Agent API Contract

This document defines the baseline API contract for `Fundamental_Agent` in the multi-agent trading system.

`Fundamental_Agent` produces fundamental-analysis signals and validation reports. It should not submit orders or bypass Manager, Risk, or Execution controls.

## Standard Headers

```http
Content-Type: application/json
X-Correlation-ID: <uuid>
X-API-KEY: <fundamental-agent-api-key>
```

## Standard Response Envelope

```json
{
  "status": "success",
  "agent_type": "fundamental",
  "version": "2.1.0",
  "schema_version": "1.0",
  "timestamp": "2026-07-04T00:00:00Z",
  "correlation_id": "00000000-0000-0000-0000-000000000000",
  "data": {},
  "metadata": {},
  "error": null,
  "confidence_score": null
}
```

## Operational Endpoints

```http
GET /health
GET /ready
GET /version
```

## Analysis Endpoints

```http
POST /analyze
POST /validate/fundamental
```

## Safety Rules

1. `Fundamental_Agent` only produces signals and validation data.
2. Confidence should remain capped before live promotion.
3. Prefetched or synthetic data must lower confidence.
4. `Fundamental_Agent` must not submit broker orders.
5. `Risk_Agent` must approve before any execution path.
6. Manager remains responsible for synthesis and orchestration.
