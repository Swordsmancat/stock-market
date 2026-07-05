# Market Data Reliability Cache and Session Governance Design

## Overview

This task adds reliability metadata and session governance around existing market-data flows, starting with intraday minute data. It does not rebuild the provider layer, does not alter existing bar-table primary keys, and does not claim production realtime parity.

The design has four boundaries:

1. A small freshness/session metadata contract.
2. A centralized intraday session policy helper.
3. Cache-safety rules for realtime-ish frontend/proxy routes.
4. Documentation and validation that preserve degraded-safe semantics.

## Existing State

- `packages/services/market_data.py` already resolves providers and returns intraday `ok` / `no_data` / `degraded` payloads.
- yfinance is the current explicit `1m` MVP provider.
- Future dates, weekends, and known yfinance US-like holidays already avoid provider minute calls in service/readiness logic.
- `DailyBar` and `MinuteBar` can store values, but not provider-specific freshness metadata.
- Daily source/freshness UI and daily quality expected-session checks already exist in archived tasks and should not be rebuilt here.

## Metadata Contract

Additive payload metadata should use stable shapes such as:

```text
freshness:
  status: fresh | stale | closed | no_data | unsupported | error | unknown
  reason: string | null
  data_as_of: string | null
  checked_at: string
  fetched_at: string | null
  cached_at: string | null
  cache_status: hit | miss | skipped | unavailable | unknown
  max_age_seconds: int | null

session:
  market: string | null
  timezone: string | null
  trading_date: YYYY-MM-DD
  status: trading_session | closed_session | current_session | weekend | known_holiday | future_date | unsupported_market | unknown
  reason: string | null
```

Fields should be optional where not applicable. Existing top-level `availability` should remain, but may include `session_state`, `cache_status`, `data_as_of`, `checked_at`, or related metadata if that is less disruptive than adding new top-level objects.

## Intraday Session Policy Boundary

Use a service helper rather than scattering conditionals. Conceptually:

```python
class IntradaySessionDecision:
    status: str
    freshness_status: str
    reason: str | None
    should_call_provider: bool
    cache_status: str
```

Initial rules:

- Unsupported provider: do not call provider; return `degraded` / `unsupported`.
- Future date: do not call provider; return `no_data` / `future_date`.
- Weekend: do not call provider; return `no_data` / `weekend`.
- Known yfinance US-like holiday: do not call provider; return `no_data` / `known_holiday`.
- Normal completed date: provider call allowed; closed-session metadata can be marked cacheable.
- Current date / unknown session: provider call allowed, but freshness should not imply realtime data.

The first implementation can keep rules in `packages/services/market_data.py` if extracting a new module is too invasive, but the helper should be cohesive and testable.

## Cache and Storage Strategy

This slice should not change existing bar-table primary keys. If persistent freshness storage is needed later, prefer a separate metadata table keyed by:

- resource type,
- provider,
- symbol,
- market,
- timeframe,
- trade date,
- session state.

For this slice, use explicit metadata and cache-safety behavior first:

- historical closed session: cacheable in principle, but only if verified rows exist;
- current session: no-store or very short TTL;
- non-session/future/known holiday: negative-cacheable in principle, but still no fabricated rows;
- unsupported provider: degraded metadata, no provider call;
- provider empty response: `no_data`, not provider failure.

## Frontend / Proxy Cache Safety

Touched realtime-ish routes should use explicit cache behavior:

- upstream fetch: `cache: "no-store"` for intraday/depth routes;
- response headers: `Cache-Control: no-store` when serving live-like or provider-specific payloads;
- preserve provider query parameters in upstream URL and tests.

Dashboard/overview can use short TTL later, but only with provider/date/session-safe cache keys. This task should avoid implementing a broad dashboard cache unless required by tests.

## Compatibility and Rollback

- All new fields are additive.
- Existing `availability` semantics remain readable by current frontend code.
- If frontend display changes are not needed, metadata can remain API-only for this slice.
- If storage/cache integration becomes risky, defer storage and deliver the policy/metadata/no-store slice first.

## Remaining Professional Gaps

After this task, remaining gaps still include:

- production live-smoke success for yfinance intraday in a reachable environment,
- full exchange calendars and half-day sessions,
- pre-market and after-hours handling,
- persistent minute cache/storage with invalidation,
- provider entitlement/quota governance,
- realtime streaming refresh,
- broader verified intraday providers.
