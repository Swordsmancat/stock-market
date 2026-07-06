# Implementation Plan

## Phase 0: Planning Gate

- [x] Create Trellis planning task.
- [x] Inspect current README, manual, prior Trellis tasks, app routes, services, and tests.
- [x] Confirm current Buffett Indicator foundation and no-data behavior.
- [x] Reframe professional comparison around information aggregation and AI research.
- [x] Ask the user to approve the first implementation slice.
- [x] Create child task `.trellis/tasks/07-06-macro-valuation-ai-brief-mvp`.
- [ ] Do not run `task.py start` until approval is given.

## P0 Slice: Macro/Valuation Indicators + AI Summary Positioning

Goal: make the product visibly about personal information aggregation and AI interpretation.

- [ ] Expand `packages/services/market_indicators.py` definitions beyond Buffett Indicator.
- [ ] Add a seed/import path for audited macro observations or documented public API adapters.
- [ ] Add tests for new indicator definitions, no-data states, and one seeded observation per indicator family.
- [ ] Improve dashboard macro/valuation UI copy so indicators are grouped and source/freshness is obvious.
- [ ] Add a dashboard-level deterministic "daily brief" from existing evidence.
- [ ] Update README and user manual to reflect the new positioning.
- [ ] Validate with:
  - `pytest tests/services/test_market_indicators_service.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py`
  - `npm run test:web -- --reporter=dot apps/web/app/[locale]/page.test.tsx`
  - full `pytest` and `npm run test:web` before closing the slice.

## P1 Slice: Citation-Aware AI Daily/Weekly Brief

Goal: make AI the primary workflow instead of raw widgets.

- [ ] Add a backend dashboard-brief service that gathers macro indicators, watchlist movement, reports, news, hot sectors, and diagnostics.
- [ ] Reuse assistant citation validation and deterministic fallback patterns.
- [ ] Add API route for dashboard-level AI summary.
- [ ] Add frontend summary panel with citations, data gaps, and "what to watch next".
- [ ] Add report persistence for daily/weekly brief history.
- [ ] Add tests for citation validation, no-data fallback, and UI rendering.

## P1 Slice: Hard-to-Find Source Collection

Goal: gather sources that are scattered across platforms.

- [ ] Define allowed source list and terms boundary.
- [ ] Add official/public macro source adapters where feasible.
- [ ] Add user-curated document or seed-file ingestion for hard-to-automate indicators.
- [ ] Add source registry documentation and freshness policy.
- [ ] Expose source/method metadata in UI and report citations.

## P2 Slice: Personal Research Notebook and Monitoring

Goal: support repeated personal research loops.

- [ ] Add personal notes linked to symbols, indicators, and reports.
- [ ] Add watchlist-specific weekly digest.
- [ ] Add saved AI briefs and follow-up questions.
- [ ] Add indicator threshold alerts if useful.
- [ ] Add export/share workflow for personal review.

## Deprioritized Optional Later Work

- Level-2/depth/order-flow production validation.
- Terminal-style configurable workstation layouts.
- Full backtesting UI.
- Broker/account integration.
- Large institutional corpus search unless source/legal boundaries are settled.

## Validation Checklist

- [ ] Existing no-fabrication behavior remains intact.
- [ ] Every new data point exposes source and as-of metadata.
- [ ] Empty or unavailable sources render explicit no-data states.
- [ ] AI output cites evidence or falls back deterministically.
- [ ] Docs do not claim investment advice, real-time data, or professional-terminal parity.
