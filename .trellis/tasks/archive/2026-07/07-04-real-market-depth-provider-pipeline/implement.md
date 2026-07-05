# Real Market Depth Provider Pipeline Implementation Plan

## Slice 1: Provider Contract and Depth Models

1. Extend `packages/providers/base.py` with explicit market-depth dataclasses:
   - `ProviderOrderBookLevel`
   - `ProviderRecentTrade`
   - `ProviderFundFlow`
   - `ProviderMarketDepthSnapshot`
   - `MarketDepthProviderAdapter`
2. Do not retrofit daily `ProviderBar` or intraday `ProviderIntradayBar` into depth data.
3. Keep `mock`, `yfinance`, `akshare`, and `tushare` as unsupported until they implement explicit `fetch_market_depth` and tests.
4. Add tests proving unsupported providers do not fabricate order book, recent trades, large orders, or fund-flow from daily/intraday data.

## Slice 2: Service Orchestration and Partial Sections

1. Refactor `packages/services/market_data.py:get_market_depth_payload` to:
   - resolve requested/effective provider as today
   - call `fetch_market_depth` only if the provider exposes the explicit depth method
   - keep unsupported providers as degraded with existing section shapes
   - normalize provider snapshots into section-level payloads
   - allow partial availability, e.g. order book ok while fund-flow degraded
2. Serialize order-book levels with `price`, `volume`, `amount`, and `order_count`.
3. Serialize recent trades with `timestamp`, `price`, `volume`, `amount`, and `side`.
4. Derive large orders only from serialized verified recent trades and the explicit threshold.
5. Serialize fund-flow with currency, net inflow fields, and `source_definition`.
6. Keep unknown provider behavior as HTTP 400 through existing `ValueError` mapping.

## Slice 3: Provider Candidate Path

1. Add an optional AkShare depth provider method only if it can be implemented behind injectable downloader callables and fixture-backed parser tests.
2. Treat AkShare runtime failures, empty responses, missing permission, and malformed payloads as degraded/no-data sections.
3. Do not mark AkShare as broadly verified in the capability matrix until an opt-in real-network smoke check has been run.
4. If live provider implementation is not stable in this task, ship the explicit provider boundary and service partial-section path with injected-provider tests, then leave AkShare production capability as candidate/unsupported.

## Slice 4: Frontend Compatibility and Tests

1. Ensure `apps/web/lib/instrument-detail.ts` preserves real `market_depth` rows from the backend.
2. Enhance `MarketDepthCard` only if needed to show section-level degraded reasons in partial support cases.
3. Add/update tests for:
   - `MarketDepthCard` rendering real order-book/recent-trade/large-order/fund-flow rows
   - partial support with top-level ok and degraded sections
   - Next instrument proxy preserving backend `market_depth` payloads
   - instrument detail page passing real depth payloads to `MarketDepthCard`

## Slice 5: Documentation and Roadmap Updates

1. Update `docs/manual/user-guide.md` with:
   - market depth remains provider/permission dependent
   - real rows appear only from explicit verified depth providers
   - large orders are derived only from verified recent trades
   - no daily/intraday/mock fabrication
2. Update `docs/runbooks/developer-maintenance.md` with:
   - depth provider contract fields
   - section-level partial semantics
   - provider capability matrix
   - validation commands
3. Update `README.md` Phase 3 market depth status based on final implementation state.
4. Record completed validation before archival.

## Validation Commands

- `python -m pytest tests/api/test_market_depth_api.py tests/services/test_market_data_service.py`
- `npx vitest run "apps/web/components/market-depth-card.test.tsx" "apps/web/app/api/instruments/[symbol]/route.test.ts" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx"`
- `npm run test:web`
- `git diff --check`

## Risk Controls

- Never derive order-book, recent-trade, large-order, or fund-flow data from daily bars, minute bars, static fixtures, or estimated distributions.
- Keep unsupported providers degraded.
- Keep provider failures typed and secret-safe.
- Large-order filtering must use an explicit threshold and verified recent trades only.
- Section-level partial support must not imply that unavailable sections are ok.
- Do not commit unrelated dirty files, especially known line-ending/noise changes.

## Completed Validation

- Backend market-depth focused tests passed: `python -m pytest tests/api/test_market_depth_api.py tests/services/test_market_data_service.py` -> `29 passed`.
- AkShare explicit depth candidate tests passed: `python -m pytest tests/providers/test_cn_market_providers.py tests/api/test_market_depth_api.py tests/services/test_market_data_service.py` -> `34 passed`.
- AkShare depth readiness script tests passed: `python -m pytest tests/scripts/test_provider_readiness.py tests/providers/test_cn_market_providers.py tests/api/test_market_depth_api.py tests/services/test_market_data_service.py` -> `41 passed`.
- AkShare depth schema diagnostics tests passed after adding safe live-failure observability: `python -m py_compile "scripts/provider_readiness.py" "packages/providers/akshare_provider.py"`; `python -m pytest tests/scripts/test_provider_readiness.py tests/providers/test_cn_market_providers.py -q` -> `19 passed`; `git diff --check -- "packages/providers/akshare_provider.py" "scripts/provider_readiness.py" "tests/scripts/test_provider_readiness.py"` -> exit code `0`.
- Live AkShare depth smoke was attempted with `python scripts/provider_readiness.py --provider akshare --market CN --symbol 600519 --check-depth --depth-levels 3 --real-network` and failed with `AkShare market-depth endpoint failed or changed schema` plus `availability_exception_type=ConnectionError`; evidence is recorded in `live-smoke.md`. The provider remains a fixture-tested candidate, not production verified.
- Frontend market-depth focused tests passed: `npx vitest run "apps/web/components/market-depth-card.test.tsx" "apps/web/app/api/instruments/[symbol]/route.test.ts" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx" --reporter=dot` -> `3 passed`, `15 tests passed`.
- Full frontend suite passed: `npm run test:web` -> `29 passed`, `97 tests passed`.
- Whitespace check passed: `git diff --check` -> exit code `0` with CRLF conversion warnings only.
- `AkShareProvider.fetch_market_depth` now exposes an injectable, fixture-tested depth candidate path that can parse order-book, recent-trade, and fund-flow shaped payloads while returning degraded availability for empty, unavailable, or schema-changed provider responses.
- `scripts/provider_readiness.py` now supports opt-in `--check-depth --real-network` readiness checks for explicit depth providers, so AkShare live schema/permission checks can be run without database writes and without default CI/network access. Depth failures can include safe diagnostics such as `availability_exception_type`, `availability_raw_shape`, `availability_raw_columns`, and `availability_raw_fields_sample` to support fixture-backed schema adaptation.
- Documentation updated in `README.md`, `docs/manual/user-guide.md`, and `docs/runbooks/developer-maintenance.md` to describe the explicit market-depth provider boundary, AkShare fixture-tested order-book candidate path, section-level partial semantics, verified-trade-only large-order derivation, provider capability matrix, and remaining professional Level-2 gaps.
- 2026-07-05 rerun: `python -m pytest tests/scripts/test_provider_readiness.py tests/providers/test_cn_market_providers.py tests/api/test_market_depth_api.py tests/services/test_market_data_service.py -q` -> `57 passed`.
- 2026-07-05 rerun: `npx vitest run "apps/web/components/market-depth-card.test.tsx" "apps/web/app/api/instruments/[symbol]/route.test.ts" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx" --reporter=dot` -> `3 passed`, `15 tests passed`.
- 2026-07-05 rerun: `python -m pytest -q` -> `286 passed`, with existing Redis `setex` deprecation warnings only.
- 2026-07-05 rerun: `npm run test:web` -> `29 passed`, `101 tests passed`.
- 2026-07-05 rerun: `git diff --check` -> exit code `0` with CRLF conversion warnings only.
