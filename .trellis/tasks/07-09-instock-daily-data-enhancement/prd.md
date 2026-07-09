# InStock Daily Data Enhancement Phase 1

## Goal

Close the next highest-value gap between this platform and `myhhub/stock` by adding research-only A-share daily flow and limit-up reason surfaces that feed the existing dashboard/research workflows without importing InStock runtime modules or enabling automatic trading.

## Background

- `docs/runbooks/instock-analysis-integration.md` says this project uses `myhhub/stock` as a staged analysis reference, not a drop-in runtime dependency.
- The current InStock-inspired slice already covers selected technical indicators, five candlestick patterns, approximate chip distribution, composite stock selection, targeted daily-bar ingestion, batch daily-bar ingestion, and three research-only strategy rules.
- The same runbook explicitly does not import InStock's indicator runtime, database, scheduler, proxy/cookie, Tornado UI, or trade modules.
- Upstream `myhhub/stock` daily data capabilities include stock fund flow, industry/concept fund flow, limit-up reasons, Dragon Tiger List, block trades, bonus/allotment data, and ETF data.
- The local repo already has a provider-backed `/sectors/hot` contract and AkShare-backed `packages/services/hot_sectors.py` implementation for sector fund-flow ranking.
- The local repo does not currently have stored models or APIs for individual stock fund-flow ranking, concept fund-flow ranking, limit-up reasons, Dragon Tiger List, or block trades.

## MVP Scope

- Add a research-only market-daily-data surface for:
  - A-share individual stock fund-flow ranking.
  - A-share industry and concept fund-flow ranking, reusing or extending the existing hot-sector provider shape where possible.
  - A-share limit-up reason rows.
- Prefer provider-backed, non-persistent API payloads for this phase unless implementation proves stored history is required for the selected UI/research flow.
- Keep provider behavior explicit: live/delayed/mock/unavailable states, provider/source metadata, as-of timestamps, sanitized diagnostics, and no fabricated numeric values.
- Add minimal frontend visibility by wiring the new payload into an existing research/market entry surface, not by building a separate full InStock clone UI.
- Update the InStock runbook/specs so the new slice is documented as research-only and bounded.

## Requirements

- R1: Add backend service contracts for A-share fund-flow and limit-up reason data with deterministic normalization and degraded/unavailable payloads.
- R2: Use AkShare as the first provider where available, but keep tests provider-fake based and not dependent on live network.
- R3: Reuse existing `/sectors/hot` semantics for industry/concept fund-flow when practical: `status`, `data_mode`, `source`, `provider`, `as_of`, `availability`, `provider_capabilities`, and item-level numeric fields.
- R4: Add a new API route only where existing routes do not fit. The API must return HTTP 200 degraded/unavailable payloads for expected provider gaps and sanitize provider exceptions.
- R5: Add frontend route/proxy/types/component rendering only for the selected MVP fields, with localized visible labels in both `apps/web/messages/en.json` and `apps/web/messages/zh.json`.
- R6: Preserve research-only boundaries: no buy/sell/hold wording, no target prices, no position sizing, no order intents, no broker calls, and no automatic trading.
- R7: Do not import InStock's runtime, scheduler, database, proxy/cookie, Tornado UI, or trade modules.
- R8: Do not create durable citations for provider-live rows in this phase unless stored local evidence rows are added with reviewed source metadata.
- R9: Add focused backend and frontend tests for successful provider rows, empty rows, provider failure, and visible degraded states.

## Out of Scope

- Automatic trading, paper trading, broker connectivity, or trade logs.
- Full InStock MySQL schema import or Tornado UI integration.
- Proxy and Cookie management.
- Full 200+ comprehensive stock-selection columns.
- Dragon Tiger List and block-trade persistence in this first phase.
- Production-grade historical backtest storage.
- Making live provider rows assistant-citable without a stored evidence model.

## Acceptance Criteria

- [x] Backend exposes normalized A-share individual stock fund-flow ranking with provider metadata and degraded/error diagnostics.
- [x] Backend exposes normalized industry/concept fund-flow ranking through the existing hot-sector shape or an explicitly documented adjacent route.
- [x] Backend exposes normalized A-share limit-up reason rows with provider metadata and degraded/error diagnostics.
- [x] Provider exceptions and empty responses never fabricate rows and never expose secrets or stack traces.
- [x] Frontend shows the new daily-data slice in an existing terminal-style research/market surface with localized labels and visible degraded states.
- [x] InStock runbook/spec docs describe the new slice, source boundary, and no-trading/no-citation limits.
- [x] Focused backend tests pass for service/API success, empty, and provider-failure cases.
- [x] Focused frontend tests pass for route/proxy/component rendering and localized states.
- [x] Type checking and `git diff --check` pass.

## Open Decision

- Resolved: Phase 1 uses individual stock fund flow + industry/concept fund flow + limit-up reasons, leaving Dragon Tiger List and block trades for Phase 2.
