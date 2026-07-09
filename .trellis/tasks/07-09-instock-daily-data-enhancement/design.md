# InStock Daily Data Enhancement Phase 1 Design

## Architecture

This task extends the existing research data stack rather than importing `myhhub/stock` as a runtime dependency.

Planned flow:

```text
AkShare provider call
  -> service normalization and diagnostics
  -> FastAPI route payload
  -> Next.js proxy / server fetch
  -> terminal-style dashboard or research component
```

No automatic trading, broker integration, upstream scheduler import, proxy/cookie workflow, or InStock database schema import is part of this slice.

## Backend Boundaries

### Existing Reuse

- `packages/services/hot_sectors.py` already defines:
  - `HotSectorProviderResult`
  - `HotSectorProviderItem`
  - `HotSectorFundFlowProvider`
  - degraded/mock/unavailable payload helpers
- `/sectors/hot` already exposes provider-backed sector fund-flow with capability metadata.
- This task should extend that route/service for industry vs concept where possible instead of creating a parallel sector-ranking model.

### New Service Surface

Add a small service module for daily market events and individual fund flow, likely under:

- `packages/services/instock_daily_data.py` or `packages/services/market_daily_data.py`
- `apps/api/routers/market_daily_data.py` or an equivalent router name

Candidate API shape:

```text
GET /market-daily-data/fund-flow/stocks?market=CN&window=today&limit=20&provider=akshare
GET /market-daily-data/limit-up-reasons?date=YYYY-MM-DD&limit=50&provider=akshare
```

If industry/concept fund-flow fits the existing route, extend:

```text
GET /sectors/hot?provider=akshare&sector_type=industry|concept&window=today&limit=10
```

## Payload Contracts

### Individual Stock Fund Flow

Top-level fields:

- `status`: `ok` / `degraded` / `unavailable`
- `data_mode`: `delayed` / `mock` / `none`
- `source`, `provider`, `requested_provider`, `effective_provider`
- `as_of`, `generated_at`, `market`, `window`
- `availability`, `provider_capabilities`
- `message`
- `count`
- `items`

Item fields:

- `symbol`, `name`, `rank`
- `latest_price`, `change_percent`
- `net_flow_amount`, `main_net_flow_amount`, `super_large_net_flow_amount`, `large_net_flow_amount`, `medium_net_flow_amount`, `small_net_flow_amount`
- `currency`, `unit`, `flow_window`
- `raw_source_fields` only if sanitized and useful for diagnostics; otherwise omit

### Limit-Up Reasons

Top-level fields mirror the fund-flow payload.

Item fields:

- `symbol`, `name`, `rank`
- `trade_date`
- `latest_price`, `change_percent`
- `reason`, `detail`, `sector`, `limit_up_count`, `consecutive_limit_up_count`
- `first_limit_up_time`, `last_limit_up_time`
- `turnover_rate`, `market_cap`
- `provider`, `source`

All fields must be optional where provider payloads omit them. Missing provider values should remain `null` or produce diagnostics, never invented zeros.

## Provider Behavior

First provider: AkShare.

Confirmed candidate functions from the installed package include:

- `stock_fund_flow_individual`
- `stock_individual_fund_flow_rank`
- `stock_fund_flow_industry`
- `stock_fund_flow_concept`
- `stock_sector_fund_flow_rank`
- `stock_lhb_detail_em`
- `stock_fund_flow_big_deal`

Limit-up reason support may need a provider method check during implementation because the installed AkShare package exposes related upstream features differently than the current InStock helper. If a reliable AkShare method is unavailable, the service should return an `unavailable` payload with a precise diagnostic rather than scraping or importing InStock.

## Persistence Decision

Phase 1 should be non-persistent provider-backed payloads.

Reasons:

- Existing `/sectors/hot` is already non-persistent and provider-backed.
- The selected UI/research value is current market context and diagnostics, not historical warehouse queries.
- Avoiding a new table keeps this phase smaller and avoids premature citation semantics.

If future tasks need assistant-citable or historical trend evidence, add dedicated ORM models, Alembic migrations, and citation contracts then.

## Frontend Boundary

Use existing frontend conventions:

- Keep visible text localized in `apps/web/messages/en.json` and `apps/web/messages/zh.json`.
- Prefer an existing terminal-style market/research surface over a standalone clone page.
- Reuse `FinancialTerminalCard` / `FinancialTerminalSurface` where the surface is a routed entry page or homepage destination.
- Render degraded/unavailable states explicitly.

Likely first placement:

- Add a compact daily-data panel to `/ai-research` or `/evidence`, or extend the market/home dashboard module if the existing data path is straightforward.

## Safety and Citation Boundary

- Live provider rows are research context only in this phase.
- Do not emit assistant citation IDs for these rows unless a future persistence slice stores reviewed evidence with stable IDs.
- UI copy must avoid trading instructions and present the data as market context.
- Any AI Research Desk usage should treat the payload as diagnostics/context unless persisted evidence is added later.

## Compatibility

- Existing `/sectors/hot` consumers must keep working if new query params are omitted.
- Existing homepage and hot-sector tests should continue to pass.
- New routes should be additive and should not change current market-data provider defaults.

## Rollback

- New API route/component files can be removed without schema rollback if Phase 1 stays non-persistent.
- If `/sectors/hot` gains query params, rollback should preserve previous default behavior for `provider` and `limit`.
