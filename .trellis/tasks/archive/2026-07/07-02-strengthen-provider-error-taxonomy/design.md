# Strengthen Provider Error Taxonomy Design

## Scope

This task refines only the market-data provider boundary and API error mapping. It does not change provider adapter implementations, successful payload shapes, ingestion, TaskRun, or frontend behavior.

## Current Boundary

- `packages/services/market_data.py` defines `MarketDataProviderError`.
- `_fetch_provider_bars(...)` and `_fetch_provider_instruments(...)` re-raise `ValueError` and wrap other provider exceptions.
- `apps/api/routers/market_data.py` maps `MarketDataProviderError` to HTTP 502 and `ValueError` to HTTP 400.

## Target Taxonomy

Use subclasses of `MarketDataProviderError` so existing catches remain compatible:

- `MarketDataProviderError`: generic provider error, category `provider_error`, HTTP 502.
- `MarketDataProviderTimeoutError`: timeout, category `timeout`, HTTP 504.
- `MarketDataProviderRateLimitError`: rate limit, category `rate_limited`, HTTP 429.
- `MarketDataProviderUnavailableError`: unavailable/connection failure, category `unavailable`, HTTP 503.
- `MarketDataProviderPayloadError`: malformed provider payload/serialization failure, category `malformed_payload`, HTTP 502.

## Classification Rules

- `ValueError` raised directly by provider operations remains a client/request error and is not wrapped.
- `TimeoutError` becomes timeout.
- `ConnectionError` becomes unavailable.
- Exception messages containing common rate-limit markers such as `rate limit`, `too many requests`, or `429` become rate-limited.
- Other unexpected exceptions remain generic provider errors.
- Serialization/payload shape failures are wrapped as malformed payload errors at the service boundary.

## API Mapping

Market-data router keeps a single provider-error catch and uses the error's `http_status_code`. Detail payload includes:

- `message`
- `provider`
- `operation`
- `category`

## Compatibility

- Existing `except MarketDataProviderError` behavior continues to catch all provider taxonomy subclasses.
- Generic `RuntimeError("provider unavailable")` remains HTTP 502 unless it is a concrete `ConnectionError`.
- Existing successful payloads and `ValueError` -> HTTP 400 behavior stay unchanged.
