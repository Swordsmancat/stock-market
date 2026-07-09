# InStock Dragon Tiger and Block Trades MVP Design

## Architecture

Extend the existing market daily data path:

```text
AkShare provider call
  -> packages/services/market_daily_data.py normalization and diagnostics
  -> apps/api/routers/market_daily_data.py FastAPI route
  -> apps/web/app/api/market-daily-data/** Next proxy
  -> apps/web/app/[locale]/ai-research/page.tsx server fetch
  -> apps/web/components/ai-research-desk.tsx compact panel
```

This task should not add database tables, ORM models, Alembic migrations, worker
jobs, scheduler entries, InStock runtime imports, proxy/cookie flows, or trading
execution code.

## Backend Design

### Service Extension

Extend `packages/services/market_daily_data.py` with:

- `DragonTigerProviderItem`
- `BlockTradeProviderItem`
- `MarketDailyDataProvider.fetch_dragon_tiger_list(trade_date, limit)`
- `MarketDailyDataProvider.fetch_block_trades(trade_date, limit)`
- `get_dragon_tiger_list_payload(...)`
- `get_block_trades_payload(...)`

Keep the top-level payload shape compatible with the existing daily-data
payloads:

- `status`: `ok` / `degraded` / `unavailable`
- `data_mode`: `delayed` / `none`
- `source`, `provider`, `requested_provider`, `effective_provider`
- `as_of`, `generated_at`, `market`, `window`, `trade_date`
- `availability`, `provider_capabilities`, `message`, `count`, `items`

### AkShare Provider Candidates

Recommended initial provider calls:

- Dragon Tiger List: start with `ak.stock_lhb_detail_em(start_date=YYYYMMDD, end_date=YYYYMMDD)`
  if the installed function signature supports the date range; otherwise return
  an explicit unavailable payload rather than guessing a scraping path.
- Block trades: start with `ak.stock_dzjy_mrmx(symbol="A股", start_date=YYYYMMDD, end_date=YYYYMMDD)`
  if the installed function signature supports the date range; otherwise return
  an explicit unavailable payload.

Before implementation, inspect signatures with `inspect.signature()` in the
local environment and code defensively around provider availability.

### API Routes

Add:

```text
GET /market-daily-data/dragon-tiger-list?date=YYYY-MM-DD&market=CN&limit=50&provider=akshare
GET /market-daily-data/block-trades?date=YYYY-MM-DD&market=CN&limit=50&provider=akshare
```

Use the same date alias behavior as `limit-up-reasons`: query parameter
`date` maps to service input `trade_date`, and missing date defaults to today.

## Frontend Design

Add two Next route proxies:

```text
apps/web/app/api/market-daily-data/dragon-tiger-list/route.ts
apps/web/app/api/market-daily-data/block-trades/route.ts
```

Update `/ai-research` server page to fetch both payloads with `limit=6` and
`provider=akshare`, matching the current daily-data fetch pattern.

Update `AiResearchDesk` local types and `MarketDailyDataPanel` to render:

- stock fund flow
- limit-up context
- Dragon Tiger List
- block trades

Keep the panel compact. Use visible degraded/unavailable messages and keep the
existing citation-boundary copy or extend it to name the new slices.

## Safety and Citation Boundary

- Live provider rows remain research context only.
- No assistant citation IDs for Dragon Tiger List or block-trade rows in this
  MVP.
- UI copy must avoid trading instructions and must not imply order execution,
  target prices, or position sizing.
- Any future storage/citation slice needs a separate reviewed contract.

## Compatibility

- Existing stock fund-flow and limit-up API behavior must remain unchanged.
- Existing AI Research Desk tests should be extended, not replaced.
- Unknown providers and provider failures should preserve HTTP 200 backend
  degraded/unavailable semantics; proxy-level backend failures may still return
  normalized 502 unavailable payloads as existing proxies do.

## Rollback

Because this MVP is non-persistent:

- Removing the new route methods, Next proxies, page fetches, and panel sections
  rolls back runtime behavior.
- No database rollback is required.
- Keep existing stock fund-flow and limit-up routes intact during rollback.
