# Independent Feature Audit and Professional Benchmark Execution

## Goal

Run an independent, Trellis-managed integration audit that is separate from the prior conversation/task `4d53d264-0019-48ab-bf4c-ecbf8bc20045`: verify which stock-market dashboard capabilities are implemented, continue any small missing implementation work, update user/developer manuals, benchmark the product against professional financial websites, and turn the remaining professionalization gaps into an executable Trellis task map.

## Background

The repository already contains two active frontend/professional-dashboard tasks. Current status supersedes the older wording below: durable screenshot evidence and explicit WCAG AA proof are now complete under `07-05-dashboard-visual-evidence-wcag`; future professional-dashboard parity remains separate roadmap scope.

- `07-03-frontend-ui-polish` — code-verifiable UI polish, movement-color system, settings persistence, browser smoke, README/manual updates, and final quality gate are documented as complete; it remains open only for durable screenshot evidence, explicit WCAG AA proof, and future professional-dashboard parity scope.
- `07-03-professional-financial-dashboard` — captures the deeper Yahoo Finance / TradingView style goal and now records that the current app is a strong internal research dashboard MVP, not a professional terminal equivalent.

The latest evidence recorded in those tasks indicates:

- `npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0` passed.
- `npm run test:web -- --reporter=dot` passed with `33 test files passed, 111 tests passed`.
- `pytest` passed with `288 tests passed`.
- Browser smoke checks for `/zh` and `/zh/settings` passed at desktop and mobile widths with no horizontal overflow and no captured console errors.
- Manuals and README were updated with the current dashboard UI state and professional-product gap plan.

The product should therefore be described as MVP-complete for the current code-verifiable dashboard/research workflow, while professional-terminal parity remains incomplete by design.

## Requirements

### 1. Independent audit scope

- Treat this task as independent from `4d53d264-0019-48ab-bf4c-ecbf8bc20045`.
- Use repository evidence, Trellis task history, tests, docs, and browser smoke results rather than assumptions.
- Do not mark professional parity complete unless the required data/provider/workflow capabilities exist and are validated.

### 2. Feature completion classification

Classify implemented capabilities into one of four states:

- **Complete for MVP** — code, tests, docs, and degraded-safe behavior are present.
- **Provider-boundary complete** — UI/API contracts exist, but production live-provider validation remains external or opt-in.
- **Evidence-only remaining** — historical/classification state for implementation that lacks durable screenshot/WCAG/manual proof; no sampled MVP UI route currently remains in this state after `07-05-dashboard-visual-evidence-wcag`.
- **Professional gap** — not implemented or intentionally out of current MVP scope.

### 3. Documentation completion

- Verify that user-facing manuals describe current implemented behavior accurately.
- Verify that developer/runbook docs describe provider readiness, degraded states, validation commands, and known professional gaps.
- Avoid marketing claims such as real-time, Level-2, institutional backtesting, or terminal-grade research corpus unless backed by validated implementation.

### 4. Professional benchmark

Compare the current app against representative professional products:

- Yahoo Finance / MarketWatch style market overview and news/dashboard density.
- TradingView style charting, workspace, indicators, alerts, and watchlists.
- Bloomberg / Koyfin / AlphaSense style institutional research, filings/transcripts/news corpus, citations, and workflow breadth.
- Eastmoney / Tonghuashun / ifind style China-market sector, fund-flow, Level-2, breadth, and rotation workflows.
- Futu / Moomoo style broker-oriented watchlist, portfolio, alerts, and quote workflows.

### 5. Trellis execution plan

- Use this task as the parent integration task.
- Reuse or link existing active tasks where they already cover part of the scope.
- Create focused child tasks only for independently verifiable follow-up work.
- Prioritize P0 correctness/evidence and no-fabrication work before P1/P2 professional convenience features.

## Acceptance Criteria

- [x] This parent task has a converged `prd.md`, `design.md`, and `implement.md`.
- [x] Existing active UI/professional-dashboard tasks are mapped or linked as child/follow-up work without duplicating their scope.
- [x] The current product status is summarized as MVP-complete vs provider-boundary vs evidence-only vs professional-gap.
- [x] Manuals/README/runbook state is verified or updated so that documentation matches implementation and does not overclaim.
- [x] A professional benchmark matrix or research artifact identifies where the app meets needs and where it falls short.
- [x] P0/P1/P2 follow-up plan is captured with Trellis task boundaries.
- [x] No code-verifiable blocker remains unaddressed without being converted into a focused task.
- [x] Final validation evidence is recorded before archiving this parent task.

## Current Completion Assessment

Based on the existing Trellis evidence, the current code-verifiable implementation is broadly complete for an internal MVP research dashboard:

- Dashboard overview, compact market ticker, market-overview table, settings-driven movement colors, watchlist, portfolio, reports, AI assistant, recommendations, chart indicators, intraday/depth degraded-safe cards, hot sectors, and manuals are present.
- Provider-boundary work exists for intraday, market depth, hot-sector metadata, AI citations, and recommendation signal evaluation; production-grade provider verification and data SLA workflows remain future work.
- UI polish is code-complete for the sampled MVP routes and now has durable screenshot artifacts plus explicit WCAG AA contrast proof.
- The product is not yet comparable to professional terminals for live feeds, Level-2/order-flow/fund-flow validation, configurable multi-panel workstations, screeners, full backtesting UI, portfolio attribution/risk, or institutional research corpus.

## 2026-07-05 P0 Evidence Closure

The evidence-only gap has now been closed by child task `07-05-dashboard-visual-evidence-wcag`:

- Durable screenshots were captured for `/zh`, `/zh/settings`, `/zh/instruments/AAPL`, and `/zh/watchlist` at `1440x900` and `390x844`.
- Raw observations recorded no console errors, no runtime-error text, and no document/body horizontal overflow across sampled routes/viewports.
- Light and dark computed-style contrast samples passed WCAG AA for sampled text sizes after a small ticker neutral-text fix.
- `07-03-frontend-ui-polish` is now archive-ready from an implementation/evidence perspective.

Updated product classification:

- **Complete for MVP**: dashboard overview, market ticker, settings-driven movement colors, market overview, watchlist, portfolios, reports, AI assistant, recommendations, chart indicators, and documented degraded states.
- **Provider-boundary complete**: intraday, depth, hot sectors, AI citations, and recommendation signal evaluation where live provider capability still depends on deployment/provider readiness.
- **Evidence-only remaining**: no blocker found for the sampled MVP routes; additional product-owner visual review can request more routes, but the Trellis evidence requirement is satisfied.
- **Professional gap**: live/low-latency feeds, Level-2/order-flow/fund-flow validation, configurable workstations, screeners, backtesting, portfolio risk attribution, and institutional research corpus.

## Recommended Follow-up Plan

### P0 — close evidence and trust gaps

1. Completed: capture durable browser screenshot artifacts for homepage/settings/instrument/watchlist at desktop and mobile widths.
2. Completed: run and record an explicit light/dark WCAG AA contrast pass.
3. Completed for frontend MVP: keep provider status, freshness, source, mock/degraded/no-data semantics visible across homepage ticker, market overview, recommendations, instrument detail, intraday chart, reports list/detail, and report generation warnings.
4. Validate production providers for intraday/depth/fund-flow before using real-time or Level-2 language.

## 2026-07-05 Provider Trust Update

Child task `07-06-provider-trust-data-sla-dashboard` implemented the selected P0 trust-visibility MVP:

- Shared frontend trust normalizer and badge/summary component.
- Homepage market overview and black ticker provider/source/freshness visibility.
- Recommendation wording changed away from unconditional realtime claims; diagnostics are visible when supplied.
- Instrument latest/K-line/intraday source, freshness, cache, session, delay, and degraded reasons are surfaced.
- Reports list/detail show source summaries, and report generation warns when no explicit provider is supplied.
- User/developer docs now explain trust labels and remaining provider-validation limits.

Validation passed with 11 focused web test files / 29 tests and the web TypeScript check. This improves no-fabrication UX but does not implement production provider SLA monitoring, entitlement/audit workflows, or professional-terminal parity.

### P1 — professional workflow gaps

1. Add screener/watchlist custom columns, saved filters, and richer alert conditions.
2. Expand sector rotation history, breadth/contribution drill-down, and real fund-flow provider integration.
3. Persist dashboard/chart workspace settings beyond the current local chart note/toggle MVP.
4. Expand AI assistant sources only after citation contracts and ingestion exist.

### P2 — terminal-grade analytics and operations

1. Add strategy backtesting UI, signal-history persistence, costs/slippage assumptions, and walk-forward validation.
2. Add portfolio attribution, exposure, factor/risk, and scenario analysis.
3. Add data SLA dashboards, provider incident history, entitlement/audit model, and usage monitoring.

## Out of Scope

- Declaring professional-terminal parity as complete in this task.
- Implementing every P1/P2 professional feature inside this parent integration task.
- Committing, pushing, or archiving tasks unless explicitly requested and validation is complete.

## Open Questions

No open planning questions remain for this parent audit task. The selected first follow-up was P0 evidence closure, which has been completed by `07-05-dashboard-visual-evidence-wcag`. Future work should be started as focused child tasks only when the next professional gap is selected.
