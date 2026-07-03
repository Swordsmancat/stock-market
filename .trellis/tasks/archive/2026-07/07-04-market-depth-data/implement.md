# Market Depth Data Implementation Plan

## Slice 1: Backend Market Depth Contract

1. Add provider depth capability metadata in `packages/services/market_data.py`.
2. Add `get_market_depth_payload` with order book, recent trades, large orders, fund-flow, and availability sections.
3. Add `GET /market-data/{symbol}/depth` to `apps/api/routers/market_data.py`.
4. Return degraded typed payloads for all current providers; do not call daily-bar provider methods to fabricate depth data.
5. Add focused pytest coverage for degraded payload, threshold override, provider defaults, and invalid query parameters.

## Slice 2: Instrument Detail Fetch Contract

1. Add TypeScript market-depth payload types in `apps/web/lib/instrument-detail.ts`.
2. Fetch `/market-data/{symbol}/depth` in `fetchInstrumentDetailPayload` as a non-fatal enhancement.
3. Add a local unavailable/degraded fallback when depth request fails.
4. Update Next route tests to assert depth request wiring and non-fatal fallback.

## Slice 3: Frontend Market Depth Card

1. Add `MarketDepthCard` using existing Card/Table/Badge primitives.
2. Render status, provider availability reason, bid/ask tables, large-order threshold, and large-order rows when present.
3. Add market-depth card to `InstrumentDetailClient` after price summary cards and before intraday chart.
4. Add English and Chinese strings under `InstrumentDetail`.
5. Add component/page tests for degraded and data-present states.

## Validation

- `python -m pytest tests/api/test_market_depth_api.py`
- `python -m pytest tests/api/test_market_depth_api.py tests/api/test_market_data_intraday_api.py tests/api/test_market_data_api.py`
- `npx vitest run "apps/web/app/api/instruments/[symbol]/route.test.ts" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx" "apps/web/components/market-depth-card.test.tsx"`
- `npm run test:web`

## Status

Completed. Backend and frontend market-depth slices now expose degraded-safe order book, recent trades, large-order, and fund-flow contracts without fabricating provider data.

## Commit Policy

Commit and push once backend/frontend market-depth slices pass focused and web tests. Do not include unrelated line-ending noise files.
