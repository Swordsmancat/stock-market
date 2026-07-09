# Market Daily Data Contract

> Executable contract for provider-backed A-share daily fund-flow and limit-up
> context surfaced for research workflows.

## Scenario: InStock-Inspired Daily Market Context

### 1. Scope / Trigger

- Trigger: `myhhub/stock` exposes daily stock fund flow, industry/concept fund
  flow, and limit-up reason workflows that are valuable research context.
- Scope: `packages/services/market_daily_data.py`,
  `packages/services/hot_sectors.py`, `apps/api/routers/market_daily_data.py`,
  `apps/api/routers/sectors.py`, Next route proxies under
  `apps/web/app/api/market-daily-data/**`, and the AI Research Desk panel.
- Non-goals: InStock runtime imports, proxy/cookie workflows, Tornado UI, MySQL
  table import, scheduler import, durable citation rows, trading
  recommendations, order intents, broker calls, or automatic trading.

### 2. Signatures

- Backend API:
  `GET /market-daily-data/fund-flow/stocks?market=CN&window=today|3d|5d|10d&limit=20&provider=akshare`
- Backend API:
  `GET /market-daily-data/limit-up-reasons?date=YYYY-MM-DD&market=CN&limit=50&provider=akshare`
- Extended backend API:
  `GET /sectors/hot?limit=5&provider=akshare&sector_type=industry|concept&window=today|5d|10d`
- Service entries:
  `get_stock_fund_flow_payload(...)`,
  `get_limit_up_reasons_payload(...)`, and
  `get_hot_sectors_payload(..., sector_type=None, window=None)`.
- Provider boundary:
  `MarketDailyDataProvider.fetch_stock_fund_flow(limit, window)` and
  `MarketDailyDataProvider.fetch_limit_up_reasons(trade_date, limit)`.

### 3. Contracts

- Phase 1 supports `market="CN"` only for these provider-backed daily-data
  endpoints.
- Payloads return HTTP 200 for expected provider gaps and use `status` values
  `ok`, `degraded`, or `unavailable`.
- Top-level fields include `status`, `data_mode`, `source`, `provider`,
  `requested_provider`, `effective_provider`, `as_of`, `generated_at`,
  `market`, `window`, optional `trade_date`, `availability`,
  `provider_capabilities`, `message`, `count`, and `items`.
- Stock fund-flow item fields include `symbol`, `name`, `rank`,
  `latest_price`, `change_percent`, `net_flow_amount`,
  `main_net_flow_amount`, `super_large_net_flow_amount`,
  `large_net_flow_amount`, `medium_net_flow_amount`,
  `small_net_flow_amount`, `currency`, `unit`, `flow_window`, `provider`, and
  `source`.
- Limit-up item fields include `symbol`, `name`, `rank`, `trade_date`,
  `latest_price`, `change_percent`, `reason`, `detail`, `sector`,
  `limit_up_count`, `consecutive_limit_up_count`, `first_limit_up_time`,
  `last_limit_up_time`, `turnover_rate`, `market_cap`, `provider`, and
  `source`.
- AkShare `stock_zt_pool_em` rows may not expose a reason/detail field. In
  that case rows may be shown as limit-up pool context only, with
  `status="degraded"` and `provider_capabilities.limit_up_reasons.status`
  set to `unavailable`.
- Live provider rows are not assistant citations in this phase. They become
  citable only after a future persistence slice stores reviewed local evidence
  with stable IDs.

### 4. Validation & Error Matrix

- Unsupported market -> HTTP 200 `status="unavailable"`, empty `items`, and a
  sanitized message.
- Unsupported fund-flow window -> HTTP 200 `status="unavailable"` and no
  provider call.
- Unknown provider -> HTTP 200 `status="unavailable"` with unavailable
  provider capabilities.
- Provider exception -> HTTP 200 `source="provider_error"` and message that
  includes only provider name and exception class, not tokens, stack traces, or
  raw request URLs.
- Provider returns no rows -> HTTP 200 `status="degraded"`,
  `data_mode="none"`, `count=0`, and no fabricated values.
- AkShare limit-up pool rows without reason/detail fields -> HTTP 200
  `status="degraded"` and visible pool rows, but no invented reason strings.

### 5. Good/Base/Bad Cases

- Good: AkShare stock fund-flow rows normalize into ranked A-share research
  context with delayed provider metadata and no citation IDs.
- Good: `/sectors/hot` defaults remain backward compatible while `sector_type`
  and `window` can request industry or concept fund-flow slices.
- Base: AkShare limit-up pool rows are available but reason text is missing;
  the UI labels the row as pool-only context and keeps reason capability
  unavailable.
- Bad: importing `instock.core.stockfetch`, InStock schedulers, proxy/cookie
  modules, or database jobs to power the endpoint.
- Bad: turning provider-live rows into `citations[]`, buy/sell/hold language,
  target prices, position sizing, or order workflows.

### 6. Tests Required

- Service tests assert stock fund-flow success, empty provider rows, unknown
  provider, unsupported windows, provider exception sanitization, limit-up
  reason success, pool-only degraded rows, and invalid dates.
- API tests assert query propagation, date alias handling, 200 unavailable
  payloads for provider gaps, and FastAPI limit validation.
- Hot-sector service/API tests assert default compatibility plus
  `sector_type`/`window` propagation.
- Frontend route tests assert backend URL normalization and normalized
  unavailable proxy payloads.
- AI Research page tests assert stock fund flow, limit-up reason/pool-only
  context, and the no-citation boundary render with localized text.

### 7. Wrong vs Correct

#### Wrong

```python
citations.append({"id": "akshare:limit_up:002001:latest", "source": "akshare"})
```

This cites a live provider row before the platform has stored reviewed local
evidence.

#### Correct

```python
return {
    "status": "degraded",
    "provider_capabilities": {
        "limit_up_reasons": {"status": "unavailable"},
        "citation": {"status": "not_citable"},
    },
    "items": [{"symbol": "002001", "reason": None}],
}
```

The row remains useful market context without becoming fabricated evidence.
