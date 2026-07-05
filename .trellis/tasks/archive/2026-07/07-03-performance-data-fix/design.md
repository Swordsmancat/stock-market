# Performance Optimization and Data Display Fix - Design

## Scope

This task improves the dashboard market-overview path without broad provider-layer rewrites. The first implementation slices should validate and harden existing cache behavior, make the frontend market filter cheaper, keep realtime-ish proxy responses cache-safe, and document the remaining provider-fallback gap.

## Current Entry Points

- Backend API: `apps/api/routers/dashboard.py`
- Backend service: `packages/services/market_dashboard.py`
- Cache helper: `packages/shared/cache.py`
- Backend tests: `tests/services/test_market_dashboard_service.py`, `tests/api/test_dashboard_api.py`
- Frontend dashboard page: `apps/web/app/[locale]/page.tsx`
- Market overview client: `apps/web/components/market-overview-client.tsx`
- Market ticker: `apps/web/components/market-ticker.tsx`
- Frontend proxy: `apps/web/app/api/market-overview/route.ts`

## Existing Behavior

- `get_market_overview_payload` is already decorated with `cache_market_overview(ttl=300)`.
- Cache keys are shaped as `dashboard:market-overview:{provider}:{YYYY-MM-DD}`.
- The backend isolates per-index/per-symbol provider failures and returns unavailable items plus diagnostics instead of failing the whole dashboard.
- The frontend proxy already calls the backend with `cache: "no-store"`.
- `MarketTicker` filters indices on every render and is not memoized.

## Target First Slices

### Slice 1 - Cache validation

Add focused tests for the existing cache helper and dashboard service cache behavior using a fake Redis client. Tests should not require a real Redis server.

### Slice 2 - Frontend display/filter performance

Use `useMemo` for derived market options and filtered ticker items, and wrap the exported ticker component with `React.memo`. This is a safe optimization because the component is a pure display component plus local filter state.

### Slice 3 - Proxy cache safety

Keep upstream backend fetches `no-store` and add explicit `Cache-Control: no-store` on the Next.js route response. Preserve the provider query parameter.

### Slice 4 - Provider fallback follow-up

Do not add broad cross-provider fallback in this slice. The existing service has partial-result resilience but not provider-chain failover. A later slice should add provider fallback only with deterministic diagnostics and tests that prove it does not use mock or fabricated data.

## Compatibility

- Keep `GET /dashboard/market-overview` response shape backward compatible.
- Keep existing provider query behavior.
- Do not fabricate data for unavailable indices.
- Do not require Redis for tests or normal fallback behavior; cache failures should not block dashboard data.

## Validation

- Backend: `python -m pytest tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py -q`
- Frontend: `npx vitest run "apps/web/app/api/market-overview/route.test.ts" "apps/web/components/market-ticker.test.tsx" --reporter=dot` if focused tests exist or are added.
- Full web: `npm run test:web` if frontend files change.
- Whitespace: focused `git diff --check` for touched files.
