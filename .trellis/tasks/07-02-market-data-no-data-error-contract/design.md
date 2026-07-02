# No-data and provider-error UX contract - Design

## Summary

Provider failures are already partly normalized through `MarketDataProviderError`, but empty market-data results are still handled inconsistently. Market-data endpoints can return empty arrays or `item: null`, while report generation assumes at least one bar and can crash with an unhandled list access error.

This task creates a backend no-data contract that is explicit enough for the frontend to render actionable states in later child tasks.

## Data-flow map

```text
Provider/DB bars
  -> packages.services.market_data.get_bars_payload()
  -> report/analysis service consumers
  -> FastAPI routers
  -> frontend pages/actions
```

Boundary decisions:

- Market-data read endpoints may return successful empty payloads because browsing a symbol/date range with no bars is not itself a server error.
- Report generation cannot proceed without bars. It should raise a typed service error instead of indexing into an empty list.
- Routers should translate typed service/provider errors to sanitized HTTP payloads.
- Worker tasks should continue recording failures through existing `TaskRun` lifecycle behavior.

## Market-data payload contract

When no bars are available, `get_bars_payload()` should keep the current successful shape and add metadata:

- `items: []`
- `status: "no_data"`
- `no_data_reason: "No daily bars were available for the requested symbol/date range."`

When bars are available:

- `status: "ok"`
- `no_data_reason: None`

`get_latest_bar_payload()` should continue returning `item: null` for no latest daily bar, with the same status/no-data metadata.

## Report/analysis error contract

Add a typed report-level error for missing market data, for example `ReportDataUnavailableError`. It should include:

- `category: "no_market_data"`
- sanitized message;
- `symbol`, `start`, `end`, `source`, and provider fields where available;
- `http_status_code: 422` for API mapping.

`generate_stock_report_payload()` should raise this error before accessing `items[0]` or `items[-1]`.

`generate_and_store_daily_report()` and `refresh_stock_analysis()` can allow the typed error to propagate. Existing worker code will record failed task runs; routers should map it to a structured 422 response.

## Router mapping

Add route-level mapping where report/analysis routers call report generation or refresh services:

- `ReportDataUnavailableError` -> HTTP 422 with `detail` object containing `message`, `category`, `symbol`, `start`, `end`, `source`, `provider`, and `no_data_reason`.
- Existing provider errors should remain sanitized and not expose original exception text or secrets.

## Test plan

- Service test: empty bars raise the typed report no-data error instead of `IndexError`.
- API report test: `/reports/{symbol}/stock` returns HTTP 422 with sanitized no-data detail.
- API daily report generation test: `/reports/{symbol}/daily/generate` returns HTTP 422 when no bars exist.
- API analysis sync test: `/analysis/refresh-sync` returns HTTP 422 when report generation has no market data.
- Market-data tests can assert no-data metadata on empty bars/latest payloads.

## Non-goals

- Do not implement frontend rendering in this child task unless a minimal test already exists nearby.
- Do not introduce real provider network tests.
- Do not change successful report payload shape.
