# Market Data Reliability Cache and Session Governance Implementation Plan

## Slice 1: Inspect Current Intraday Metadata Flow

1. Read `packages/services/market_data.py`, intraday API tests, provider readiness tests, and frontend proxy/page tests before editing.
2. Identify the exact existing fields in intraday `ok`, `no_data`, and `degraded` payloads.
3. Keep all existing fields stable.

## Slice 2: Add Freshness and Session Metadata

1. Add a small helper for intraday freshness/session metadata.
2. Reuse existing no-data reason constants for future, weekend, known holiday, unsupported provider, and provider empty response.
3. Add metadata for:
   - `freshness.status`,
   - `freshness.reason`,
   - `freshness.checked_at`,
   - `freshness.data_as_of`,
   - `freshness.cache_status`,
   - `session.status`,
   - `session.trading_date`,
   - `session.reason`.
4. Keep metadata additive and optional.

## Slice 3: Centralize Provider-Call Decisions

1. Consolidate provider skip decisions for unsupported provider, future date, weekend, and known holiday.
2. Ensure skipped scenarios do not call `fetch_intraday_bars`.
3. Ensure normal trading dates still call explicit intraday provider methods.
4. Align readiness skip reasons with service skip reasons where practical.

## Slice 4: Cache Safety for Frontend Proxies

1. Inspect touched Next.js API routes for intraday/depth/market overview.
2. Add `cache: "no-store"` / `Cache-Control: no-store` only where needed and tested.
3. Ensure provider query parameters remain in upstream URLs.
4. Avoid broad dashboard caching unless explicitly required by the slice.

## Slice 5: Tests and Documentation

1. Update service/API tests for intraday metadata across ok/no_data/degraded paths.
2. Update provider readiness tests if helper alignment changes output details.
3. Update frontend proxy tests if no-store/cache headers are changed.
4. Update runbook/user guide if metadata is user-visible.
5. Record validation here before finish.

## Validation Commands

Backend focused validation:

```bash
python -m pytest tests/services/test_market_data_service.py tests/api/test_market_data_intraday_api.py tests/scripts/test_provider_readiness.py -q
```

Frontend focused validation if proxy/UI changes:

```bash
npx vitest run "apps/web/app/api/instruments/[symbol]/route.test.ts" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx" "apps/web/components/intraday-price-chart.test.tsx" --reporter=dot
```

Full frontend validation if frontend code changes:

```bash
npm run test:web
```

Whitespace check:

```bash
git diff --check -- "packages/services/market_data.py" "scripts/provider_readiness.py" "tests/services/test_market_data_service.py" "tests/api/test_market_data_intraday_api.py" "tests/scripts/test_provider_readiness.py" "apps/web/app/api/instruments/[symbol]/route.test.ts" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx" "apps/web/components/intraday-price-chart.test.tsx"
```

## Risk Controls

- Do not change `bars_1d` or `bars_1m` primary keys in this task.
- Do not fabricate intraday minute rows from daily bars, mock rows, or previous close.
- Do not mark AkShare/Tushare/mock as verified intraday providers.
- Do not claim full exchange-calendar coverage.
- Do not add broad cache storage without provider/symbol/timeframe/date-safe keys.
- Do not break current `ok` / `no_data` / `degraded` intraday semantics.
- Do not commit unrelated dirty files.

## Completed Validation

- Backend focused validation passed after adding additive intraday `freshness` and `session` metadata for `ok`, `no_data`, and `degraded` paths: `python -m py_compile "packages/services/market_data.py"`; `python -m pytest tests/services/test_market_data_service.py tests/api/test_market_data_intraday_api.py tests/scripts/test_provider_readiness.py -q` -> `51 passed`.
- Targeted regression for the previously failing no-data metadata paths passed: `python -m pytest tests/services/test_market_data_service.py::test_get_intraday_bars_payload_returns_no_data_for_empty_verified_provider tests/services/test_market_data_service.py::test_get_intraday_bars_payload_returns_weekend_no_data_without_minute_provider_call tests/api/test_market_data_intraday_api.py::test_get_intraday_returns_weekend_no_data_without_minute_provider_call -q` -> `3 passed`.
- IDE diagnostics passed for edited market-data files: `ReadLints` -> `0 diagnostics`.
- Whitespace check passed for market-data reliability files: `git diff --check -- "packages/services/market_data.py" "tests/services/test_market_data_service.py" "tests/api/test_market_data_intraday_api.py" "tests/scripts/test_provider_readiness.py"` -> exit code `0` with CRLF conversion warnings only.
- Documentation updated in `docs/runbooks/developer-maintenance.md` and `docs/manual/user-guide.md` to describe intraday `freshness` / `session` metadata, the meaning of `cache_status`, and remaining professional gaps around persistent minute cache, full calendars, half days, pre/post-market, streaming, and provider entitlement.
