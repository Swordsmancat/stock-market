# Market Daily Evidence Persistence MVP

## Goal

Persist selected provider-backed daily market context rows as local, reviewed
research evidence so AI Research, dashboard briefs, saved research briefs, and
the market assistant can cite stable local IDs without treating live provider
responses as evidence.

## User Value

The platform already surfaces A-share stock fund-flow, limit-up, Dragon Tiger
List, block-trade, and hot-sector/fund-flow context. Today those rows are useful
on screen but explicitly not citable. This task turns the most valuable daily
rows into durable research evidence with diagnostics, dedupe, and citation
boundaries, so later AI summaries can say where a claim came from.

## Confirmed Facts

- `packages/services/market_daily_data.py` provides normalized, provider-backed
  payloads for:
  - `GET /market-daily-data/fund-flow/stocks`
  - `GET /market-daily-data/limit-up-reasons`
  - `GET /market-daily-data/dragon-tiger-list`
  - `GET /market-daily-data/block-trades`
- `packages/services/hot_sectors.py` provides normalized hot-sector/fund-flow
  context through `GET /sectors/hot`.
- `.trellis/spec/backend/market-daily-data-contract.md` states that live
  provider rows are not assistant citations until a future persistence slice
  stores reviewed local evidence with stable IDs.
- `docs/runbooks/instock-analysis-integration.md` applies the same
  no-citation boundary to stock fund-flow, limit-up, Dragon Tiger List,
  block-trade, and provider-backed hot-sector rows.
- `packages/domain/models.py` already contains local evidence precedents:
  `DailyBar`, `TechnicalIndicator`, `FundamentalSnapshot`,
  `MarketIndicatorObservation`, `NewsArticle`, `GeneratedReport`,
  `ResearchSourceNote`, and `ResearchBrief`.
- `packages/services/market_assistant.py` and
  `packages/services/market_dashboard.py` validate citation IDs against
  allowed prefixes. `market_daily_event:` is not yet an allowed prefix.
- Existing migration/test style is SQLAlchemy model + Alembic revision +
  domain migration tests under `tests/domain/test_migrations.py`.

## Requirements

- R1: Add durable storage for normalized market daily evidence rows without
  importing InStock runtime modules, proxy/cookie flows, Tornado UI, scheduler
  jobs, or trading modules.
- R2: Store enough metadata to make each row auditable: `event_type`, `symbol`
  or sector identity, `market`, `trade_date`, `provider`, `source`, `as_of`,
  provider availability/capability metadata, normalized value payload, and
  import timestamp.
- R3: Use deterministic dedupe/upsert keys so repeated imports for the same
  provider/date/type/identity update or preserve rows without duplicating
  evidence.
- R4: Expose service/API workflows to import provider-backed market daily
  context into storage with fake-provider tests and no live-network dependency.
- R5: Generate stable citation IDs only from persisted rows, recommended shape:
  `market_daily_event:<event_type>:<identity>:<trade_date>`.
- R6: Add citation builders that can surface stored market daily evidence to the
  market assistant and related research/dashboard surfaces without breaking
  existing response contracts.
- R7: Keep source boundaries explicit: live provider payloads remain
  non-citable; only persisted rows from this task can become
  `market_daily_event:*` citations.
- R8: Preserve no-trading boundaries: no buy/sell/hold wording, no target
  prices, no position sizing, no order intents, no broker calls, and no
  automatic trading.
- R9: Return sanitized diagnostics for provider/import/storage failures and
  never expose API keys, raw provider secrets, stack traces, or hidden prompts.
- R10: Add backend tests for migration/model shape, service import/upsert,
  citation generation, assistant/dashboard citation gating, and API behavior.
- R11: Include `hot_sector` rows in this MVP using the same persistence,
  citation, diagnostics, and no-trading boundaries as the four
  `/market-daily-data/*` row types.
- R12: Successful provider-normalized imports become immediately citable as
  local provider-verified evidence. Manual review states/workflows are out of
  scope for this MVP.
- R13: Add a minimal frontend entry on an existing research/evidence surface to
  show stored market daily evidence availability, recent import metadata, and
  `market_daily_event:*` citations. Do not create a standalone market-events
  page in this MVP.
- R14: The minimal frontend entry includes a "refresh today's market evidence"
  action that triggers the import API for the default MVP event types, then
  refreshes the visible summary and diagnostics.

## Candidate Event Types

- `stock_fund_flow`
- `limit_up_reason`
- `dragon_tiger_list`
- `block_trade`
- `hot_sector`

## Out of Scope

- Automatic trading, paper trading, broker connectivity, or order workflows.
- Full historical backfill or scheduler automation beyond a manual/import API
  MVP.
- Manual review workflow for market daily evidence rows before citation.
- Standalone market-events explorer, advanced filtering, graph analytics, or
  historical event comparison UI.
- Custom event-type picker, scheduler controls, bulk historical backfill, or
  long-running job monitor for the refresh action.
- Full InStock database schema import or Tornado UI integration.
- Proxy/cookie scraping workflows requiring a new legal/provider review.
- Vector search, embeddings, raw document storage, or licensed corpus ingestion.
- Turning live provider rows directly into citations without local persistence.

## Acceptance Criteria

- [x] A migration and SQLAlchemy model persist market daily evidence rows with
  deterministic uniqueness and JSON payload metadata.
- [x] Import service writes normalized provider payload rows using fake-provider
  tests and handles empty/provider-error payloads without fabricated evidence.
- [x] Import API returns inserted/updated/skipped counts plus sanitized
  diagnostics.
- [x] Stored evidence citation builder emits `market_daily_event:*` IDs only for
  persisted rows and never for live provider payloads.
- [x] Successfully persisted provider-normalized rows are immediately eligible
  for stored citation assembly; no draft/review-pending state is required in
  this MVP.
- [x] Market assistant and research/dashboard citation validation include the new
  prefix only after stored evidence is assembled.
- [x] UI/research surfaces can display stored market daily evidence availability
  or citations without implying trading advice.
- [x] Existing frontend research/evidence surface shows a minimal stored market
  daily evidence entry with localized labels, counts, latest import metadata,
  and citation IDs.
- [x] Frontend refresh action imports today's default market daily evidence,
  reports inserted/updated/skipped counts or sanitized failure diagnostics, and
  refreshes the displayed summary.
- [x] Specs/runbooks document the storage contract, citation ID shape, dedupe
  rules, diagnostics, and no-trading boundary.
- [x] Focused backend tests pass for migration, service, API, and citation
  integration.
- [x] Frontend tests pass for any touched visible research/citation surface.
- [x] `ruff`, TypeScript if touched, Trellis validation, and `git diff --check`
  pass.

## Resolved Decisions

- Resolved: Include `hot_sector` rows alongside the four
  `/market-daily-data/*` row types.
- Resolved: Provider-normalized rows become citable immediately after
  successful local persistence. Manual review remains a later workflow.
- Resolved: Add a minimal frontend entry on an existing research/evidence
  surface; do not create a standalone market-events page.
- Resolved: Include a minimal refresh action for today's default market daily
  evidence event types.
