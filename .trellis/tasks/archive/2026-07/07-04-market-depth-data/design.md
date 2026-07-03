# Market Depth Data Design

## Boundaries

This task introduces a degraded-safe market-depth contract and an instrument-detail UI surface for level-2 style data.

The first implementation slice is contract-first:

- Backend exposes a typed depth payload with order book, recent trades, large orders, and fund-flow sections.
- Current providers are explicitly marked as unsupported/degraded rather than returning fabricated mock depth.
- Instrument detail fetches market depth as a non-fatal enhancement, just like intraday data.
- Frontend renders a market-depth card with clear unavailable/degraded states and table structures that can display real data later.

## Backend Contract

Add a dedicated endpoint:

```http
GET /market-data/{symbol}/depth?depth_levels=5&large_order_threshold_amount=1000000&provider=...
```

The endpoint returns HTTP 200 for expected unavailable/degraded states. Invalid query parameters remain HTTP 422 through FastAPI validation, and unsupported provider names continue to use the existing HTTP 400 boundary.

Payload shape:

```json
{
  "symbol": "AAPL",
  "source": "none",
  "provider": "yfinance",
  "requested_provider": "yfinance",
  "effective_provider": "yfinance",
  "status": "degraded",
  "as_of": null,
  "is_realtime": false,
  "is_delayed": false,
  "delay_minutes": null,
  "order_book": {
    "status": "degraded",
    "reason": "The selected provider does not expose verified market depth data in this backend.",
    "as_of": null,
    "depth_levels": 5,
    "bids": [],
    "asks": []
  },
  "recent_trades": {
    "status": "degraded",
    "reason": "Recent trades are not normalized or verified by this backend yet.",
    "as_of": null,
    "items": []
  },
  "large_orders": {
    "status": "degraded",
    "reason": "Large order detection requires verified recent trades, which are unavailable.",
    "threshold_amount": 1000000.0,
    "threshold_volume": null,
    "currency": null,
    "as_of": null,
    "items": []
  },
  "fund_flow": {
    "status": "degraded",
    "reason": "Fund-flow data is not normalized or verified by this backend yet.",
    "as_of": null,
    "currency": null,
    "net_inflow": null,
    "main_net_inflow": null,
    "retail_net_inflow": null,
    "source_definition": null
  },
  "availability": {
    "status": "degraded",
    "reason": "The selected provider does not expose verified market depth data in this backend.",
    "capabilities": {
      "order_book": false,
      "recent_trades": false,
      "large_orders": false,
      "fund_flow": false
    }
  }
}
```

## Provider Capability Matrix

The initial capability matrix marks all current providers as unsupported for verified depth/trades/fund-flow data:

- `mock`: no verified real market depth; do not fabricate order book data.
- `yfinance`: no verified level-2 market depth through this backend.
- `akshare`: future candidate for CN depth/fund-flow data, but not normalized or verified yet.
- `tushare`: future candidate depending on API permissions, but not normalized or verified yet.

## Large Order Threshold

The default threshold is explicit and returned in every payload:

- `DEFAULT_LARGE_ORDER_THRESHOLD_AMOUNT = 1000000.0`
- Query override: `large_order_threshold_amount`

Large-order `items` remain empty until verified recent trades are available.

## Frontend Contract

Extend `InstrumentDetailPayload` with optional `market_depth`.

The market-depth fetch is non-fatal:

- Daily bars remain the fatal dependency for the detail page.
- Intraday and market depth can degrade independently.
- Missing `market_depth` is rendered as unavailable rather than crashing.

## UI Placement

Add `MarketDepthCard` in `InstrumentDetailClient` after the three price summary cards and before the intraday card.

The card renders:

- Status badge and availability reason.
- Five-level bid/ask table when levels exist.
- Large-order table when items exist.
- Empty/degraded text when data is unavailable.

## Testing

- Backend tests cover the degraded payload, capability matrix, threshold value, and invalid query validation.
- Frontend route tests cover depth request wiring and non-fatal fallback.
- Component/page tests cover ok/degraded/unavailable rendering.
