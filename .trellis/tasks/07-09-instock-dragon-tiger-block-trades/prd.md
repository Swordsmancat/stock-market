# InStock Dragon Tiger and Block Trades MVP

## Goal

Add the next research-only `myhhub/stock`-inspired daily market context slice by
surfacing A-share Dragon Tiger List and block-trade activity through the existing
provider-backed market daily data stack, without importing InStock runtime
modules or enabling trading workflows.

## Background

- `docs/runbooks/instock-analysis-integration.md` treats `myhhub/stock` as a
  staged analysis reference, not a runtime dependency.
- The previous daily-data phase added non-persistent provider-backed endpoints
  for A-share individual stock fund-flow, industry/concept fund-flow, and
  limit-up pool/reason context.
- `packages/services/market_daily_data.py` already owns normalized daily market
  context payloads with `status`, `data_mode`, `provider`, `source`, `as_of`,
  `generated_at`, `market`, `trade_date`, `availability`,
  `provider_capabilities`, `message`, `count`, and `items`.
- `apps/api/routers/market_daily_data.py` already exposes `/market-daily-data/*`
  routes that return HTTP 200 degraded/unavailable payloads for expected
  provider gaps.
- `apps/web/app/[locale]/ai-research/page.tsx` already fetches selected
  market-daily-data payloads, and `apps/web/components/ai-research-desk.tsx`
  renders a compact A-share daily-data panel.
- Local AkShare capability inspection found Dragon Tiger List candidates such as
  `stock_lhb_detail_em`, `stock_lhb_stock_detail_em`, `stock_lhb_yybph_em`, and
  block-trade candidates such as `stock_dzjy_mrmx`, `stock_dzjy_mrtj`,
  `stock_dzjy_sctj`, `stock_dzjy_hygtj`, and `stock_dzjy_yybph`.

## MVP Scope

- Add provider-backed, non-persistent A-share Dragon Tiger List rows.
- Add provider-backed, non-persistent A-share block-trade rows.
- Use AkShare as the first provider where available, but keep tests provider-fake
  based and free of live network dependency.
- Reuse the existing market daily data service/router/proxy pattern rather than
  creating a separate InStock clone module.
- Add compact AI Research Desk visibility for the two new daily-data slices.
- Update the runbook/spec contracts so the new rows remain research context only
  and non-citable until a future persistence/review slice exists.

## Requirements

- R1: Extend backend service contracts for Dragon Tiger List and block trades
  with deterministic normalization and sanitized degraded/unavailable payloads.
- R2: Add FastAPI routes for:
  - `GET /market-daily-data/dragon-tiger-list?date=YYYY-MM-DD&market=CN&limit=50&provider=akshare`
  - `GET /market-daily-data/block-trades?date=YYYY-MM-DD&market=CN&limit=50&provider=akshare`
- R3: Keep Phase 1 market support to `market="CN"` and return explicit
  unavailable payloads for unsupported markets, invalid dates, unknown providers,
  provider exceptions, or empty provider rows.
- R4: Normalize item fields without inventing missing values. Missing numeric
  provider fields stay `null`; empty provider responses return empty `items`.
- R5: Add Next.js route proxies under `apps/web/app/api/market-daily-data/**`
  with query normalization, no-store backend fetches, and normalized unavailable
  proxy payloads.
- R6: Render the new slices in an existing research/market surface with localized
  labels in both `apps/web/messages/en.json` and
  `apps/web/messages/zh.json`.
- R7: Preserve the research-only boundary: no buy/sell/hold wording, no target
  prices, no position sizing, no order intents, no broker calls, and no automatic
  trading.
- R8: Do not emit assistant citation IDs for live provider rows. They become
  citable only after a future persistence/review contract stores stable local
  evidence rows.
- R9: Do not import InStock runtime, schedulers, database modules, proxy/cookie
  code, Tornado UI, or trade modules.
- R10: Add focused backend and frontend tests for success, empty rows, provider
  failure, invalid input, proxy failures, and visible degraded states.

## Candidate Item Fields

Dragon Tiger List item fields should be additive and optional:

- `symbol`, `name`, `rank`, `trade_date`
- `close_price`, `change_percent`, `turnover_rate`, `amount`
- `net_buy_amount`, `buy_amount`, `sell_amount`
- `reason`, `department_name`, `department_rank`
- `provider`, `source`

Block-trade item fields should be additive and optional:

- `symbol`, `name`, `rank`, `trade_date`
- `trade_price`, `close_price`, `discount_percent`
- `volume`, `amount`
- `buyer`, `seller`, `market`
- `provider`, `source`

## Out of Scope

- Automatic trading, paper trading, broker connectivity, or order workflows.
- Durable storage/citation IDs for Dragon Tiger List or block-trade rows.
- Full InStock database schema import or Tornado UI integration.
- Proxy/cookie workflows or scraping paths that require a new legal/provider
  review.
- Seat-level historical analytics, participant graph analysis, or backtesting.
- Dragon Tiger List / block-trade rows as assistant-citable evidence.

## Acceptance Criteria

- [x] Backend exposes normalized Dragon Tiger List payloads with provider metadata,
  degraded/unavailable diagnostics, and no fabricated rows.
- [x] Backend exposes normalized block-trade payloads with provider metadata,
  degraded/unavailable diagnostics, and no fabricated rows.
- [x] Provider exceptions and empty responses never expose secrets, stack traces,
  raw URLs, or invented numeric values.
- [x] Frontend route proxies forward normalized queries and return normalized
  unavailable payloads on backend/proxy failure.
- [x] AI Research Desk shows Dragon Tiger List and block-trade context with
  localized labels and visible degraded/unavailable states.
- [x] Runbook/spec docs describe the new slice, source boundary, and
  no-trading/no-citation limits.
- [x] Focused backend service/API tests pass.
- [x] Focused frontend route/page tests pass.
- [x] `ruff`, TypeScript, Trellis validation, and `git diff --check` pass.

## Open Decision

- Resolved: Dragon Tiger List and block trades will be implemented together in
  one MVP slice. The first UI placement extends the existing AI Research Desk
  market-daily-data panel with non-persistent provider-backed sections. Durable
  storage/citations, deeper seat/participant analytics, and a standalone market
  events page remain later phases.
