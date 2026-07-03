# Phase 2 Hardening Acceptance Closure Implementation Plan

## Steps

1. Inspect the current chart, recommendation, hot-sector, and comparison implementations.
2. Add MA60 and YTD support to the advanced candlestick chart.
3. Make recommendation cards link to instrument detail pages and update tests if needed.
4. Add direct backend tests for breakout and oversold/rebound recommendations.
5. Add explicit status/source handling for hot sectors in API/UI.
6. Enrich comparison export with summaries and correlations.
7. Run focused tests:
   - `npx vitest run "apps/web/app/[locale]/page.test.tsx"`
   - `npx vitest run "apps/web/lib/comparison-utils.test.ts"`
   - `python -m pytest tests/api/test_recommendations_api.py`
8. Run `npm run test:web` after frontend changes.
9. Check lints for edited frontend files.
10. Commit and push only this slice and its Trellis planning artifacts.

## Review Gates

- Do not mark the whole Phase 2 task complete just because this slice passes; update the parent audit matrix instead.
- Do not claim real sector data is live if the current payload is still demo/mock.
- Do not include unrelated working tree noise in the commit.
