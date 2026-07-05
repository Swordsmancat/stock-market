# Persistent Intraday Cache and Calendar Governance - Design

## Scope

This child task adds the first real persistent-cache behavior behind the existing intraday minute endpoint. It builds on the previous additive `freshness` / `session` metadata slice and keeps the public API backward compatible.

The target is a conservative, testable v1:

- Reuse the existing `MinuteBar` / `bars_1m` persistence path for verified minute bars where safe.
- Serve historical closed-session minute data from cache after a successful provider-backed fetch.
- Keep current-session requests provider-first unless the implementation can label cached data as stale/incomplete without changing the public contract.
- Keep session-policy skips ahead of provider and cache fabrication for future dates, weekends, known holidays, and unsupported providers.

## Existing Evidence

- `packages/domain/models.py` already defines `MinuteBar` with `__tablename__ = "bars_1m"` and OHLCV fields keyed by `instrument_id` and timestamp.
- `alembic/versions/0001_core_schema.py` creates `bars_1m`, so a base minute-bar table already exists.
- `packages/services/market_data.py` exposes `get_intraday_bars_payload(...)` and already returns additive `freshness` and `session` metadata for `ok`, `no_data`, and `degraded` paths.
- `tests/services/test_market_data_service.py` and `tests/api/test_market_data_intraday_api.py` already cover verified provider intraday responses, unsupported providers, future dates, weekends, and metadata behavior.

## Data Model Strategy

### Primary storage

Use `bars_1m` as the minute-bar cache for provider-verified intraday bars.

The table already captures the core immutable bar facts:

- instrument identity
- timestamp
- open / high / low / close
- volume
- amount

### Cache metadata

The implementation should first inspect whether existing schema or nearby tables can represent source/provider metadata. If not, add the smallest compatible metadata extension needed to make cache decisions explainable. Acceptable options, in preference order:

1. Reuse an existing source/provider column or related metadata table if present and compatible.
2. Add nullable additive columns to `bars_1m` only if they do not break existing inserts/tests.
3. Add a narrow sidecar metadata table keyed by provider, symbol/instrument, trade date, timeframe, and cache write time if row-level schema changes are too invasive.

Any metadata path must support these cache decisions:

- provider that produced the rows
- timeframe (`1m` for this task)
- trade date
- first/last timestamp or data-as-of
- fetched/written time
- enough status information to distinguish cache hit, miss, skipped, stale, and unavailable paths in `freshness`

## Service Flow

The intraday service should evaluate requests in this order:

1. Normalize symbol, provider, trade date, and timeframe.
2. Reject or degrade unsupported providers/timeframes using the existing response semantics.
3. Classify session-policy skips before any cache or provider fabrication:
   - future date
   - weekend
   - known provider/symbol holiday
4. For historical closed sessions:
   - check persistent cache for verified rows matching symbol/instrument, provider, trade date, and timeframe;
   - if usable rows exist, return `ok` with `freshness.cache_status = "hit"` and session metadata;
   - if rows do not exist, call the verified provider path;
   - persist provider-returned rows and return `ok` with `freshness.cache_status = "miss"` or an equivalent miss/fetched status.
5. For current sessions:
   - prefer the existing provider-first behavior for v1;
   - if cache participates, label the result with conservative freshness metadata so users do not mistake stale partial data for realtime coverage.
6. For provider-empty responses on valid historical sessions:
   - return the existing `no_data` semantics;
   - do not persist fake minute bars;
   - optionally persist only metadata if the design chooses a no-data marker, but this must not block future provider retries unless explicitly bounded.

## Public Contract

The existing endpoint remains unchanged:

```text
GET /market-data/{symbol}/intraday?date=YYYY-MM-DD&timeframe=1m
```

Existing statuses remain valid:

- `ok`
- `no_data`
- `degraded`

Additive metadata remains the compatibility surface:

```text
freshness.cache_status = hit | miss | skipped | unavailable | unknown
freshness.status       = fresh | stale | closed | no_data | unsupported | error | unknown
session.status         = trading_session | closed_session | current_session | weekend | known_holiday | future_date | unsupported_market | unknown
```

The task should not require frontend changes unless a newly exposed metadata value needs display support. Existing consumers should continue to work if they ignore the new cache semantics.

## Calendar / Session Boundaries

This task keeps the known lightweight calendar strategy already introduced for yfinance-style US equities:

- future-date skip
- weekend skip
- fixed/observed holiday skip
- already-supported movable holiday skip

Out of scope:

- commercial-grade global exchange calendars
- half-days / early closes
- pre-market and after-hours sessions
- CN/HK-specific trading calendars unless already represented in existing code

## Validation Strategy

- Unit-test service-level cache miss then provider fetch then persist.
- Unit-test repeated historical request returning cache hit without calling provider.
- Unit-test session-policy skips still avoid provider calls and do not write fake bars.
- Unit-test unsupported provider path still returns `degraded` with session/freshness metadata.
- Keep API-level tests focused on response shape and metadata rather than external provider behavior.
- Keep all tests offline by using fake providers and temporary test databases.

## Rollout and Rollback

- Rollout is additive: existing API fields and statuses remain unchanged.
- If metadata columns or a sidecar table are added, migration must be reversible through normal Alembic downgrade conventions.
- If cache reads cause unexpected behavior, the service can temporarily bypass cache reads and retain provider-first behavior while leaving persisted data unused.
- If cache writes fail, the endpoint should prefer returning provider data with cache metadata marked unavailable instead of failing an otherwise usable market-data response.

## Open Product Decision

Recommended v1 decision: cache and serve only historical closed sessions from persistent storage; keep current sessions provider-first. This is the safest professional-facing behavior because it avoids presenting stale partial minute bars as realtime coverage.
