# Intraday Chart Implementation Plan

## Slice 1: Backend Intraday Contract

1. Add a degraded-safe intraday payload builder in `packages/services/market_data.py`.
2. Add `GET /market-data/{symbol}/intraday` in `apps/api/routers/market_data.py`.
3. Return `degraded` when the selected provider does not support verified minute bars.
4. Return HTTP 400 for unsupported intraday timeframe values.
5. Add focused API tests for degraded payload and invalid timeframe.

## Slice 2: Instrument Detail Fetch Contract

1. Extend `InstrumentDetailPayload` with optional intraday payload types.
2. Fetch intraday data in `fetchInstrumentDetailPayload` as a non-fatal enhancement.
3. Degrade intraday failures to a local unavailable payload while keeping latest/daily bars successful.
4. Update route tests for backend intraday request and degradation.

## Slice 3: Frontend Intraday Card

1. Add `IntradayPriceChart` with lightweight-charts line, optional average line, previous-close price line, optional volume histogram, and localized detail strip.
2. Add intraday card to `InstrumentDetailClient` above the daily K-line card.
3. Add English and Chinese strings.
4. Add component/page tests for available and degraded states.

Status: completed. The backend exposes a degraded-safe `/market-data/{symbol}/intraday` contract; instrument detail fetches intraday as a non-fatal enhancement; and the frontend renders a standalone localized intraday chart card with available and degraded states.

## Validation

- `python -m pytest tests/api/test_market_data_intraday_api.py`
- `python -m pytest tests/api/test_market_data_api.py tests/api/test_market_data_intraday_api.py`
- `npx vitest run "apps/web/app/api/instruments/[symbol]/route.test.ts" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx" "apps/web/components/intraday-price-chart.test.tsx"`
- `npm run test:web`

## Commit Policy

Commit and push once the intraday backend/frontend slice passes focused and web tests. Do not include unrelated line-ending noise files.
