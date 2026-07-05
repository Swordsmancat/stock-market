# Intraday Chart Design

## Boundaries

This task adds a degraded-safe intraday chart experience for instrument detail pages.

The implementation is split across backend and frontend layers:

- Backend owns the minute-data availability contract.
- The existing instrument detail fetcher includes intraday as an optional enhancement.
- The frontend renders intraday data in its own chart card so failures do not break the daily K-line chart.

## Backend Contract

Add a dedicated endpoint:

```http
GET /market-data/{symbol}/intraday?date=YYYY-MM-DD&timeframe=1m&provider=...
```

The endpoint returns HTTP 200 for expected unavailable/degraded states. Invalid request parameters remain HTTP 400 through the existing router error boundary.

Payload shape:

```json
{
  "symbol": "AAPL",
  "timeframe": "1m",
  "date": "2026-07-03",
  "source": "none",
  "provider": "yfinance",
  "requested_provider": "yfinance",
  "effective_provider": "yfinance",
  "status": "degraded",
  "previous_close": null,
  "items": [],
  "availability": {
    "status": "degraded",
    "reason": "The selected provider does not support verified minute bars in this backend.",
    "is_realtime": false,
    "is_delayed": false,
    "delay_minutes": null
  }
}
```

Supported status values:

- `ok`: verified minute bars are available.
- `no_data`: minute-bar capability exists, but no points are available for the requested date.
- `degraded`: the selected provider/backend cannot provide verified minute bars.

Current provider adapters do not provide verified minute bars. The initial backend slice therefore returns a stable `degraded` payload instead of calling daily-only provider methods and accidentally mislabeling daily bars as minute data.

## Frontend Contract

Extend `InstrumentDetailPayload` with an optional `intraday` object that mirrors the backend payload and is non-fatal:

- Daily bars remain the main data source for the K-line chart.
- Intraday fetch failure degrades to a local unavailable payload.
- Instrument detail pages keep rendering latest price and daily K-line data even when intraday is unavailable.

## Intraday Chart Component

Add a standalone `IntradayPriceChart` component rather than expanding `AdvancedCandlestickChart`.

Responsibilities:

- Render intraday price as a line series.
- Render average price as an optional line series when present.
- Render previous close as a price line when present.
- Render volume as an optional histogram series.
- Show a DOM detail strip for the latest point or hovered point.
- Render a localized degraded/empty state when points are unavailable.

The first slice may ship with the degraded state wired from backend contract. The component should still support available points so real minute data can be added later without another UI rewrite.

## Compatibility

- Do not fabricate live intraday points from daily bars.
- Do not treat the previous daily bar as previous close unless it is explicitly returned by the intraday payload.
- Keep the existing daily K-line card behavior unchanged.
- Preserve existing provider symbol mapping in `apps/web/lib/instrument-detail.ts`.

## Testing

- Backend API tests cover degraded intraday payload and invalid timeframe.
- Frontend route/detail tests cover intraday degradation without failing the full detail payload.
- Component tests cover empty/degraded and available chart states.
