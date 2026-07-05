# Persistent Intraday Cache and Calendar Governance

## Goal

Add the next market-data reliability slice after intraday `freshness` / `session` metadata: a persistent, bounded, provider-transparent cache for verified intraday minute bars, plus stronger calendar/session governance so repeated requests for the same trading date are reliable, explainable, and do not repeatedly hit upstream providers when data is already known or session policy says no market data should exist.

This task should move the intraday endpoint closer to professional financial-site expectations without claiming full realtime infrastructure, full global exchange calendars, or Level-2 market data.

## Requirements

- Preserve the existing public endpoint and compatibility contract:
  - `GET /market-data/{symbol}/intraday?date=YYYY-MM-DD&timeframe=1m` remains the primary API.
  - Existing response statuses remain valid: `ok`, `no_data`, and `degraded`.
  - Existing response fields remain backward compatible; new fields must be additive.
- Cache only verified provider-returned minute bars.
  - Do not fabricate minute bars from daily bars, previous close, indicators, or mock fallbacks.
  - Do not treat unsupported providers as cacheable market data.
  - Do not write fake rows for future dates, weekends, or known market holidays.
- Add persistent cache behavior for provider-backed intraday bars:
  - Historical closed sessions can be served from cache after a successful provider fetch.
  - Repeated requests for the same symbol / provider / trade date / timeframe should avoid unnecessary provider calls when cache data is usable.
  - Cache entries must carry enough metadata to explain provider, timeframe, trade date, write time, source, and freshness decision.
- Keep session governance explicit:
  - Future dates, weekends, and known provider/symbol market holidays should be classified before provider calls.
  - Unsupported providers should return the existing degraded path without attempting cache fabrication.
  - Current-session behavior must be conservative: if caching current-session data is supported, stale or incomplete data must be labelled clearly; otherwise current sessions may remain provider-first with explicit metadata.
- Keep the existing `freshness` and `session` metadata model and extend it only when necessary.
  - `freshness.cache_status` should distinguish cache hit, cache miss, skipped provider call, and unavailable/unknown cache state.
  - `freshness.data_as_of`, `checked_at`, `fetched_at`, `cached_at`, and `max_age_seconds` should be meaningful when the cache participates in the decision.
  - `session.status` and `session.reason` should continue to explain no-data and closed/current/future/weekend/holiday decisions.
- Prefer small, testable backend changes.
  - Focus on yfinance-style verified `1m` intraday data first.
  - Do not broaden AkShare/Tushare intraday production support unless this can be done without speculative data semantics.
  - Do not introduce a streaming/realtime subsystem in this task.
- Update documentation/manuals to explain the cache/session behavior accurately.
  - Clearly state that persistent intraday cache improves repeatability but is not a full realtime market data plant.
  - Clearly state known calendar limitations, including partial sessions / half-days and non-US exchanges if not implemented.

## Constraints

- Preserve unrelated uncommitted worktree changes.
- Do not change `bars_1d` semantics or primary keys.
- Do not change response shape in a way that breaks existing frontend/API tests.
- Avoid external network access during normal automated tests.
- Provider readiness and live-smoke commands must remain opt-in for real network access.
- If a database schema change is required, it must be narrowly scoped, reversible, and covered by model/service tests.

## Acceptance Criteria

- [x] Intraday cache storage exists for verified minute bars or a documented existing storage path is reused safely.
- [x] Successful provider-backed intraday fetches can be persisted with provider, symbol, trade date, timeframe, and cache metadata.
- [x] Repeated historical closed-session requests can return `ok` from cache without calling the upstream provider.
- [x] Empty/no-data policy paths for future dates, weekends, known holidays, and unsupported providers still avoid data fabrication and preserve `no_data` / `degraded` semantics.
- [x] `freshness` metadata differentiates cache hits, cache misses, skipped provider calls, and stale/unavailable conditions where applicable.
- [x] `session` metadata remains present on `ok`, `no_data`, and `degraded` paths.
- [x] Existing intraday API/service tests continue to pass, with new focused tests for cache hit/miss and session policy behavior.
- [x] Documentation explains the new cache behavior, limitations, and professional-benchmark impact.
- [x] No automated test requires live external market-data network access.

## Notes

- This is a complex child task because it may touch backend service logic, domain persistence, tests, and documentation.
- The previous `07-05-market-data-cache-session-governance` slice added metadata only; this task should add actual persistence/reuse where safe.
- Full exchange calendars, half-day handling, pre/post-market support, realtime streaming, and Level-2/tick data remain out of scope unless explicitly split into later child tasks.
