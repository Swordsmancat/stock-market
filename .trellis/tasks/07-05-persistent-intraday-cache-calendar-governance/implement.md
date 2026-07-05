# Persistent Intraday Cache and Calendar Governance - Implementation Plan

## Execution Order

1. Re-read current task artifacts and applicable Trellis specs before code changes.
2. Inspect `MinuteBar`, `bars_1m` migration, market-data service flow, database/session helpers, and existing intraday tests.
3. Decide the smallest metadata strategy after inspection:
   - reuse existing metadata if available;
   - otherwise add a nullable additive metadata path or narrow sidecar table.
4. Add service helpers for persistent intraday cache lookup and serialization.
5. Add service helpers for persisting verified provider-returned minute bars.
6. Integrate cache lookup only for historical closed sessions after session-policy skip checks and before provider calls.
7. Preserve current-session provider-first behavior for v1 unless cache freshness can be labelled safely.
8. Update `freshness` metadata so cache hits and cache misses are distinguishable.
9. Add focused offline tests for:
   - provider fetch then cache write;
   - repeated historical request served from cache without provider call;
   - future/weekend/holiday skip without provider or fake cache writes;
   - unsupported provider degraded path;
   - cache write failure falling back to provider response when feasible.
10. Update documentation/manuals to describe the persistent intraday cache and limitations.
11. Run focused backend tests and any migration/model tests touched by schema changes.
12. Record validation results and remaining professional-benchmark gaps in this task file.

## Implementation Gate

Implementation may begin only after all of these are true:

- `prd.md`, `design.md`, and this `implement.md` have been reviewed.
- The user approves starting this child task implementation.
- The task is activated with `task.py start 07-05-persistent-intraday-cache-calendar-governance`.
- Applicable Trellis specs have been loaded through `trellis-before-dev`.
- Target source/test files are read immediately before editing.

## Candidate Files to Inspect Before Editing

- `packages/domain/models.py`
- `alembic/versions/0001_core_schema.py`
- latest Alembic revision under `alembic/versions/`
- `packages/services/market_data.py`
- database/session utility modules under `packages/` and `apps/api/`
- `tests/services/test_market_data_service.py`
- `tests/api/test_market_data_intraday_api.py`
- `tests/domain/test_migrations.py`
- `docs/manual/user-guide.md`
- `docs/runbooks/developer-maintenance.md`

## Validation Commands

Use the narrowest commands that cover edited behavior:

```powershell
python -m py_compile "packages/services/market_data.py" "packages/domain/models.py"
python -m pytest tests/services/test_market_data_service.py tests/api/test_market_data_intraday_api.py tests/domain/test_migrations.py -q
```

If an Alembic migration is added, also run the repository's migration-focused tests or extend `tests/domain/test_migrations.py` as appropriate.

If documentation only changes after backend validation, use a read-through/manual Markdown validation rather than introducing unrelated build work.

## Rollback Points

- After schema decision: if a migration is not necessary, avoid creating one.
- After cache read helpers: provider-first behavior can be restored by bypassing the cache lookup branch.
- After cache write helpers: if persistence is unreliable, retain provider response and mark cache metadata as unavailable.
- After documentation changes: docs can be reviewed independently from runtime code.

## Risk Controls

- Never fabricate minute bars.
- Do not cache unsupported provider responses as market data.
- Do not suppress provider retries forever based on a single empty response unless a bounded no-data marker is explicitly implemented and tested.
- Keep current-session semantics conservative.
- Keep tests offline with fake providers and temporary/local database state.

## Completion Evidence To Record

- Exact schema/model changes, if any.
- Cache hit/miss behavior and how provider calls are avoided.
- Freshness/session metadata examples for hit, miss, skipped, and degraded paths.
- Focused test command output.
- Documentation updates and remaining limitations.

## Completion Evidence

- Schema/model: reused `bars_1m` for minute OHLCV facts and added `IntradayMinuteCacheEntry` / `intraday_minute_cache_entries` as sidecar metadata keyed by provider, symbol, trade date, and timeframe.
- Cache behavior: historical closed-session requests check sidecar metadata and `bars_1m` before provider calls; cache hits return `source="cache"` and `freshness.cache_status="hit"` without calling provider.
- Miss/write behavior: verified provider rows return `source="provider"`, `freshness.cache_status="miss"`, and are persisted for later reuse. Cache write/read failures return provider data with `freshness.cache_status="unavailable"`.
- Session policy: future dates, weekends, known yfinance US-like holidays, and unsupported providers avoid minute-bar fabrication; policy skips use `freshness.cache_status="skipped"` and session metadata.
- Documentation/spec: updated `docs/manual/user-guide.md`, `docs/runbooks/developer-maintenance.md`, and `.trellis/spec/backend/intraday-cache-contract.md`.
- Validation:
  - `python -m py_compile packages/services/market_data.py packages/domain/models.py packages/providers/yfinance_provider.py scripts/provider_readiness.py`
  - `python -m pytest tests/services/test_market_data_service.py tests/api/test_market_data_intraday_api.py tests/providers/test_yfinance_provider.py tests/scripts/test_provider_readiness.py tests/domain/test_migrations.py -q` -> 67 passed.
  - `python -m pytest -q` -> 286 passed, 3 existing Redis `setex` deprecation warnings.
- Remaining limitations: current-session cache reuse, full global calendars, half-days, pre/post-market sessions, realtime streaming, Level-2/tick data, longer historical minute retention, and multi-provider validation remain follow-up work.
