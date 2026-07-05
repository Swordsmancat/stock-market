# Market Data Reliability Cache and Session Governance

## Goal

Improve market-data reliability by adding a focused freshness/session governance layer around the existing provider-backed market-data flows, starting with intraday minute data. The task must keep current API contracts backward compatible, avoid fabricated data, and make provider/source/session/cache state explicit enough for users and maintainers to distinguish fresh, stale, closed-session, no-data, unsupported, and provider-error states.

## User Value

Users should understand whether market data is current, stale, unavailable because a market session is closed, or unavailable because a provider lacks verified data. The platform should avoid unnecessary provider calls for obvious non-session dates and prevent frontend/proxy caching from silently showing the wrong provider or stale live-like data.

## Confirmed Facts

- `DailyBar` and `MinuteBar` tables already exist, but their primary keys do not include provider/source and they do not carry full freshness metadata such as fetched time, cache status, last attempt, or last success.
- The archived source-freshness table task already added day-bar source/provider/as-of/freshness visibility to the instrument detail path. This task should not rebuild that UI.
- The archived trading-calendar quality task already added optional expected-trade-date support to daily data-quality checks. This task should not reimplement that pure function.
- The real intraday minute pipeline task delivered yfinance `1m` provider-backed MVP semantics with `ok`, `no_data`, and `degraded` payloads, previous-close reference, no daily-bar fabrication, and provider readiness checks.
- Current intraday session governance already covers future dates, weekends, and known yfinance US-like symbol holidays. It is still not a complete exchange calendar/session policy.
- Market-depth, intraday, hot-sector, and AI assistant payloads already rely on degraded-safe principles. This task should preserve those principles and add metadata, not introduce hard failures for expected unavailable states.
- Frontend provider selection exists, but frontend/proxy cache policy must be explicit for realtime-ish routes to avoid stale or cross-provider responses.

## Requirements

### R1. Preserve Existing Contracts

- Keep public endpoint contracts backward compatible, especially `GET /market-data/{symbol}/intraday?date=YYYY-MM-DD&timeframe=1m`.
- Keep existing intraday statuses: `ok`, `no_data`, and `degraded`.
- Add metadata fields only as optional, additive fields.
- Do not change `bars_1d` or `bars_1m` primary keys in this first slice.

### R2. Introduce Freshness and Session Metadata

- Add a small reusable metadata shape for market-data responses where applicable.
- Metadata should be able to express:
  - provider / requested provider / effective provider,
  - source kind such as provider, database, cache, or none,
  - data as-of time or trade date,
  - checked/fetched/cached time when known,
  - freshness status,
  - session state,
  - reason for no-data, stale, unsupported, closed, or error states.
- Initial status vocabulary should cover at least `fresh`, `stale`, `closed`, `no_data`, `unsupported`, `error`, and `unknown`.

### R3. Centralize Intraday Session Policy

- Consolidate existing intraday rules for future dates, weekends, known yfinance US-like holidays, unsupported providers, and normal trading dates into a reusable service/helper boundary.
- Service payload generation and provider readiness should use the same policy or shared helper logic where practical.
- Obvious non-session cases must skip provider minute-bar calls and return explanatory `no_data` or `degraded` metadata.
- The helper must not claim full global exchange-calendar coverage. Unknown markets should remain explicit `unknown` rather than guessed.

### R4. Add Cache/Freshness Governance without Over-Engineering Storage

- Define an intraday cache/freshness policy for historical closed sessions, current sessions, future/non-session dates, provider empty responses, and unsupported providers.
- First implementation may be metadata-focused and service-local if persistent storage would require broader schema migration.
- If storage is added later, it should use a separate metadata table instead of changing `DailyBar` / `MinuteBar` primary keys.
- Cache keys must include provider, symbol, timeframe, trade date, and session/freshness-relevant dimensions to avoid cross-provider data leakage.

### R5. Frontend and Proxy Cache Safety

- Realtime-ish frontend proxy routes for intraday/depth/market overview should avoid accidental Next.js/browser caching.
- Provider query parameters must be preserved through proxy routes.
- If cache headers or `cache: "no-store"` are added, tests should prove the behavior for affected routes.

### R6. Documentation and Professional Gap Tracking

- Update developer/user docs if payload metadata or cache/session semantics become visible.
- Record that this task is a reliability MVP, not production-grade realtime market-data infrastructure.
- Keep remaining gaps explicit: production live-smoke success, full exchange calendars, half days, pre/post-market, streaming, provider entitlement, and persistent minute cache/storage if deferred.

## Acceptance Criteria

- [x] Intraday service/API payloads remain backward compatible while exposing additive `freshness` and/or `session` metadata for `ok`, `no_data`, and `degraded` scenarios.
- [x] Tests prove future, weekend, and known-holiday intraday requests do not call provider minute endpoints and include stable session/freshness reasons.
- [x] Tests prove unsupported providers remain `degraded` and expose `unsupported` metadata without daily-bar fabrication.
- [x] Tests prove normal trading dates still call the explicit intraday provider method when needed.
- [x] Provider readiness checks stay opt-in for network calls and align skip reasons with service session policy.
- [x] Frontend proxy tests cover no-store or equivalent cache-safety behavior where routes are touched.
- [x] Existing focused intraday and provider-readiness tests still pass.
- [x] Documentation and this task's implementation notes record completed validation and remaining professional gaps.

## Completion Status

The reliability MVP is complete for intraday minute payloads: `freshness` and `session` metadata are additive across `ok`, `no_data`, and `degraded` paths; future, weekend, known-holiday, unsupported-provider, and provider-empty states remain no-fabrication paths; provider readiness remains opt-in for network access; and documentation records the remaining professional gaps.

Persistent production-grade minute storage, full exchange calendars, half days, pre/post-market sessions, streaming, provider entitlement, and multi-provider verified intraday expansion remain follow-up work.

## Out of Scope

- Full commercial-grade exchange calendar integration.
- Realtime streaming or websocket refresh.
- Level-2 order book, tick, recent-trade, or broker entitlement work.
- AkShare/Tushare verified intraday provider broadening.
- Rebuilding the already completed daily source/freshness table UI.
- Changing `bars_1d` / `bars_1m` primary keys.
- AI assistant retrieval, chart workspace, and recommendation backtesting.

## Recommended First Slice

Implement the metadata/session policy layer first for intraday minute data, then extend route/cache headers only where tests show a concrete stale-cache risk. Persistent minute storage/cache should remain a second slice unless the repository already has a low-risk integration point.
