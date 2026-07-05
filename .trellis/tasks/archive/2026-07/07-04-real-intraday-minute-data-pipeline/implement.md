# Real Intraday Minute Data Pipeline Implementation Plan

## Slice 1: Provider Contract and yfinance Intraday Fetch

1. Extend `packages/providers/base.py` with an explicit `ProviderIntradayBar` dataclass and narrow intraday provider protocol/helper.
2. Add `YFinanceProvider.fetch_intraday_bars(symbol, trade_date, timeframe)`.
3. Keep `YFinanceProvider.fetch_bars(..., timeframe="1d")` behavior unchanged for daily bars.
4. Forward `interval="1m"` to yfinance only from the explicit intraday method.
5. Normalize minute `DatetimeIndex` rows into provider intraday bars.
6. Return an empty list for empty/malformed provider responses rather than fabricating rows.
7. Add provider tests for:
   - yfinance downloader receives `interval="1m"`
   - minute timestamps are preserved
   - empty DataFrame returns `[]`
   - missing OHLCV columns do not produce fake rows
   - unsupported intraday timeframe raises `ValueError`

## Slice 2: Service and API Payloads

1. Refactor `packages/services/market_data.py:get_intraday_bars_payload` to:
   - keep `timeframe="1m"` validation
   - resolve requested/effective provider
   - route only explicit intraday-capable providers to real minute fetches
   - keep mock/akshare/tushare unsupported and degraded
   - return `status="ok"` for verified minute rows
   - return `status="no_data"` for verified provider empty results
   - preserve `status="degraded"` for unsupported providers
2. Serialize each minute bar with `timestamp`, `open`, `high`, `low`, `close`, `price`, `average_price`, `volume`, and `amount`.
3. Compute `previous_close` through daily bars as a reference only, looking back several calendar days and never using daily bars as minute rows.
4. Keep FastAPI router signature unchanged.
5. Add service/API tests for:
   - yfinance real minute payload
   - empty yfinance minute payload returns `no_data`
   - unsupported providers return degraded and do not call daily `fetch_bars("1m")`
   - unsupported timeframe still maps to HTTP 400
   - previous-close lookup succeeds when daily history exists and is optional when absent

## Slice 3: Frontend Compatibility and Tests

1. Confirm `apps/web/lib/instrument-detail.ts` preserves intraday `status="ok"` payload fields.
2. Keep failed intraday backend requests as degraded proxy fallback.
3. Add/update tests for:
   - Next instrument detail proxy preserves real intraday `ok` items
   - instrument page/detail path passes real intraday points to `IntradayPriceChart`
   - existing degraded intraday tests still pass
4. Avoid adding a new frontend status value unless backend introduces it in this task.

## Slice 4: Documentation and Roadmap Updates

1. Update `docs/manual/user-guide.md`:
   - yfinance can provide verified 1m minute bars when available
   - unsupported providers remain degraded/unavailable
   - yfinance historical 1m retention can lead to `no_data`
   - daily bars are used only for previous-close reference
2. Update `docs/runbooks/developer-maintenance.md`:
   - endpoint contract for real intraday payloads
   - provider capability matrix: yfinance supports verified 1m MVP; mock/akshare/tushare remain unsupported
   - focused validation commands
3. Update README Phase 3 intraday status from degraded-only partial to provider-backed MVP once implementation and tests pass.
4. Record completed validation in this file before archival.

## Validation Commands

- `python -m pytest tests/providers/test_yfinance_provider.py tests/services/test_market_data_service.py tests/api/test_market_data_intraday_api.py`
- `npx vitest run "apps/web/app/api/instruments/[symbol]/route.test.ts" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx" "apps/web/components/intraday-price-chart.test.tsx"`
- `npm run test:web`
- `git diff --check`

## Completed Validation

- Backend provider/service/API focused tests passed: `python -m pytest tests/providers/test_yfinance_provider.py tests/services/test_market_data_service.py tests/api/test_market_data_intraday_api.py` -> `30 passed`.
- Provider readiness, intraday, and market-depth focused tests passed: `python -m pytest tests/scripts/test_provider_readiness.py tests/providers/test_yfinance_provider.py tests/providers/test_cn_market_providers.py tests/api/test_market_data_intraday_api.py tests/api/test_market_depth_api.py tests/services/test_market_data_service.py` -> `56 passed`.
- Provider readiness diagnostics tests passed after adding the intraday lookback window: `python -m pytest tests/scripts/test_provider_readiness.py -q` -> `13 passed`.
- Provider readiness future-date guard tests passed after skipping future explicit trade dates before provider minute calls: `python -m py_compile "scripts/provider_readiness.py"`; `python -m pytest tests/scripts/test_provider_readiness.py -q` -> `15 passed`; `git diff --check -- "scripts/provider_readiness.py" "tests/scripts/test_provider_readiness.py"` -> exit code `0`.
- Intraday known US fixed/observed holiday guard tests passed after skipping yfinance US-like symbol holiday sessions before provider minute calls: `python -m py_compile "packages/services/market_data.py" "scripts/provider_readiness.py"`; `python -m pytest tests/services/test_market_data_service.py tests/api/test_market_data_intraday_api.py tests/scripts/test_provider_readiness.py -q` -> `48 passed`; `git diff --check -- "packages/services/market_data.py" "tests/services/test_market_data_service.py" "tests/api/test_market_data_intraday_api.py" "scripts/provider_readiness.py" "tests/scripts/test_provider_readiness.py"` -> exit code `0` with CRLF conversion warnings only.
- Intraday common US movable-holiday guard tests passed after adding MLK Day, Presidents Day, Good Friday, Memorial Day, Labor Day, and Thanksgiving handling for yfinance US-like symbols: `python -m py_compile "packages/services/market_data.py" "scripts/provider_readiness.py"`; `python -m pytest tests/services/test_market_data_service.py tests/api/test_market_data_intraday_api.py tests/scripts/test_provider_readiness.py -q` -> `51 passed`; `git diff --check -- "packages/services/market_data.py" "tests/services/test_market_data_service.py" "tests/api/test_market_data_intraday_api.py" "scripts/provider_readiness.py" "tests/scripts/test_provider_readiness.py"` -> exit code `0` with CRLF conversion warnings only.
- Intraday weekend session-governance tests passed after adding explanatory weekend `no_data`: `python -m py_compile "packages/services/market_data.py"`; `python -m pytest tests/services/test_market_data_service.py tests/api/test_market_data_intraday_api.py -q` -> `28 passed`; `git diff --check -- "packages/services/market_data.py" "tests/services/test_market_data_service.py" "tests/api/test_market_data_intraday_api.py"` -> exit code `0` with CRLF conversion warnings only.
- Intraday future-date session-governance tests passed after adding explanatory future-date `no_data`: `python -m py_compile "packages/services/market_data.py"`; `python -m pytest tests/services/test_market_data_service.py tests/api/test_market_data_intraday_api.py -q` -> `30 passed`; `git diff --check -- "packages/services/market_data.py" "tests/services/test_market_data_service.py" "tests/api/test_market_data_intraday_api.py"` -> exit code `0` with CRLF conversion warnings only.
- Live yfinance intraday smoke was attempted with `python scripts/provider_readiness.py --provider yfinance --market US --symbol AAPL --check-intraday --trade-date 2026-07-03 --real-network` and failed with no verified `1m` bars in the current environment; evidence is recorded in `live-smoke.md`. The implementation remains provider-backed MVP, not broadly production verified.
- Frontend route/page/chart focused tests passed: `npx vitest run "apps/web/app/api/instruments/[symbol]/route.test.ts" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx" "apps/web/components/intraday-price-chart.test.tsx" --reporter=dot` -> `3 passed`, `13 passed`.
- Full frontend suite passed: `npm run test:web` -> `29 passed`, `94 passed`.
- Whitespace check passed: `git diff --check` -> exit code `0` with CRLF conversion warnings only.
- `scripts/provider_readiness.py` now supports opt-in `--check-intraday --real-network` readiness checks for explicit intraday providers, so yfinance live minute-bar checks can be run without database writes and without default CI/network access. When `--trade-date` is omitted, the smoke tries a bounded recent-weekday window controlled by `--intraday-lookback-days` (default 5); when `--trade-date` is provided, it preserves the single-date check.
- `scripts/provider_readiness.py` now skips explicit future `--trade-date` intraday checks with a non-writing `WARN`, avoiding avoidable live-provider calls for sessions that cannot exist yet.
- `scripts/provider_readiness.py` and `get_intraday_bars_payload` now recognize known US equity holidays for yfinance US-like symbols, including fixed/observed holidays, common movable holidays, and the 2026-07-03 Independence Day observed holiday that previously caused confusing live-smoke failures.
- `get_intraday_bars_payload` now treats weekend dates as session-governed `no_data` before calling the provider minute endpoint, while still allowing daily bars to provide `previous_close`; this avoids avoidable provider calls and keeps no-fabrication semantics explicit.
- `get_intraday_bars_payload` now treats future dates as session-governed `no_data` before calling the provider minute endpoint, avoiding avoidable live-provider requests for sessions that cannot exist yet.
- Documentation updated in `README.md`, `docs/manual/user-guide.md`, and `docs/runbooks/developer-maintenance.md` to describe the yfinance `1m` provider-backed MVP, `ok` / `no_data` / `degraded` semantics, previous-close handling, opt-in intraday readiness checks, and remaining professional gaps.

## Risk Controls

- Do not reuse daily `fetch_bars("1m")` as intraday data.
- Do not mark mock, AkShare, or Tushare minute data as verified until they have explicit intraday provider methods and tests.
- Preserve degraded-safe payloads for unsupported providers.
- Keep `timeframe="1m"` as the only supported MVP timeframe.
- Treat empty yfinance results as `no_data`, not provider failure.
- Do not commit unrelated dirty files, especially known line-ending/noise changes.
