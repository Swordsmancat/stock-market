# Performance Optimization and Data Display Fix - Implementation Plan

## Execution Order

1. Read backend dashboard service/cache/tests and frontend market overview/ticker/proxy files before editing.
2. Preserve the existing dashboard payload shape and provider query contract.
3. Add deterministic cache tests around the existing Redis helper and service decorator.
4. Add small frontend performance improvements to market filtering only: `useMemo` and `React.memo`.
5. Add explicit no-store response headers to the market-overview proxy if tests can cover it.
6. Run focused backend tests.
7. Run focused frontend tests if added, then `npm run test:web` for frontend changes.
8. Record which PRD acceptance criteria are now satisfied and which remain deferred.

## First Slice Checklist

- [ ] Cache key and TTL behavior covered by tests without a real Redis server.
- [ ] Cache read/write failures remain non-fatal.
- [ ] Market ticker filtering uses memoized derived data.
- [ ] Market ticker remains a pure client component with local filter state.
- [ ] Market-overview proxy preserves provider query and uses explicit no-store cache behavior.
- [ ] Backend dashboard focused tests pass.
- [ ] Frontend focused/web tests pass after frontend changes.
- [ ] Remaining provider fallback and runtime performance-benchmark gaps are documented rather than overclaimed.

## Deferred Follow-ups

- Cross-provider automatic fallback by market with attempted-provider diagnostics.
- Runtime benchmark evidence for `<500ms` cache-hit and `<2s` cold-load goals.
- LCP and market-filter timing instrumentation.
- Browser-level validation that all available indices render in production-like data conditions.
- WebSocket or streaming refresh.

## Validation Commands

```powershell
python -m pytest tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py -q

npx vitest run "apps/web/app/api/market-overview/route.test.ts" "apps/web/components/market-ticker.test.tsx" --reporter=dot

npm run test:web

git diff --check -- packages/shared/cache.py packages/services/market_dashboard.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py apps/web/components/market-ticker.tsx apps/web/app/api/market-overview/route.ts apps/web/app/api/market-overview/route.test.ts apps/web/components/market-ticker.test.tsx .trellis/tasks/07-03-performance-data-fix/design.md .trellis/tasks/07-03-performance-data-fix/implement.md .trellis/tasks/07-03-performance-data-fix/prd.md
```

## Risk Controls

- Do not add mock data to make the dashboard look complete.
- Do not treat unavailable/no-data indices as live quotes.
- Do not make Redis a hard dependency for dashboard rendering.
- Do not add provider-chain fallback without tests that prove attempted providers and final effective provider are explicit.
- Do not commit unrelated dirty files.
