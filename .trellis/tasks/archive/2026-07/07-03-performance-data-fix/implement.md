# Performance Data Fix - Completion Notes

## Implemented Scope

- Dashboard market-overview payload is cached by provider and date through `cache_market_overview(ttl=300)`.
- The Redis write path uses `redis_client.set(..., ex=ttl)` to avoid deprecated `setex` warnings while preserving the same TTL behavior.
- The dashboard service keeps partial results when an index provider fails instead of failing the entire page payload.
- The localized homepage uses bounded optional fetches, no-store backend fetches, SWR refresh for the client market overview, and visible freshness/status fields.
- Provider selection is centralized through platform settings and the backend provider-resolution path, with explicit unavailable/degraded payloads in later feature tasks instead of silent mock-as-live behavior.

## Validation

```powershell
python -m pytest tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py -q
# 4 passed
```

## Remaining Professional Follow-up

- Runtime performance should still be measured in a live environment before claiming a hard SLA such as p95 `<500ms`.
- Broader provider routing, market-calendar governance, and monitoring remain tracked by follow-up market-data reliability tasks.
