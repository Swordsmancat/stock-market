# Strengthen provider error taxonomy

## Goal

Strengthen market-data provider error taxonomy so upstream failures are easier to classify, test, and map to API responses without changing successful market-data payloads.

## Background

Current market-data service code wraps unexpected provider failures in `MarketDataProviderError` and maps them to HTTP 502. Known request/input errors such as unsupported timeframes can still propagate as `ValueError` and become HTTP 400. The remaining backlog calls out a need to distinguish provider unavailable, timeout, rate limit, and malformed upstream payload cases while preserving existing API compatibility.

## Requirements

- Keep `ValueError` from provider/service request validation mapped to HTTP 400.
- Preserve the existing generic provider failure behavior for ordinary unexpected provider exceptions.
- Add typed provider error categories for timeout, rate limit, provider unavailable, and malformed provider payload cases.
- Add API error details that expose provider, operation, and category without exposing secrets.
- Wrap malformed provider payload/serialization failures at the market-data service boundary instead of leaking raw `AttributeError` or `TypeError`.
- Keep successful market-data, indicator, latest-bar, and market-snapshot payload shapes unchanged.
- Add focused service and API tests for the new taxonomy.

## Acceptance Criteria

- [x] Generic unexpected provider failures still raise `MarketDataProviderError` and map to HTTP 502.
- [x] Provider timeout failures raise a typed timeout provider error and map to HTTP 504.
- [x] Provider rate-limit failures raise a typed rate-limit provider error and map to HTTP 429.
- [x] Provider unavailable failures raise a typed unavailable provider error and map to HTTP 503.
- [x] Malformed provider bar payloads raise a typed malformed-payload provider error and map to HTTP 502.
- [x] API error details include `provider`, `operation`, and `category` for provider errors.
- [x] Existing market-data service/API tests continue to pass.

## Out of Scope

- Rewriting provider adapters or adding provider-specific SDK exception dependencies.
- Changing successful payload schemas.
- Adding retry/backoff behavior.
- Changing ingestion, TaskRun, or frontend behavior.

## Validation

```bash
python -m pytest tests/services/test_market_data_service.py tests/api/test_market_data_api.py -v
```
