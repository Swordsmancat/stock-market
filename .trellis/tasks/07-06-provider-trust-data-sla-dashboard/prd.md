# Provider Trust and Data SLA Dashboard

## Goal

Close the next P0 professionalization gap by making provider trust, data freshness, mock/degraded/no-data states, and non-realtime/unsupported-provider semantics visible on the main financial-data surfaces. The product must not imply realtime, Level-2, complete fund-flow, or provider-verified data unless the payload explicitly supports that claim.

## Background

The parent audit task `07-05-independent-feature-audit-professional-execution` concluded that the current product is a solid MVP research dashboard but not professional-terminal parity. The completed evidence child task `07-05-dashboard-visual-evidence-wcag` closed screenshot and WCAG evidence gaps. The next P0 gap is data trust.

A read-only provider-trust audit found that backend and service payloads already expose many trust fields, but frontend presentation is inconsistent:

- Market overview payloads include `provider`, `status`, `freshness`, `source`, `requested_provider`, `effective_provider`, `generated_at`, and `no_data_reason`, but the UI only shows a limited status badge.
- Intraday payloads include `availability`, `freshness`, and `session`, but the frontend type and chart do not surface most of those fields.
- Market depth and hot sectors already have relatively complete degraded/mock/delayed/provider metadata displays.
- Recommendations use user-facing wording such as realtime/realtime technical signals without enough payload evidence for realtime status.
- Reports persist `source_summary`, but report list/detail pages do not make the source/provider visible; report generation can silently use `mock` if no provider is passed.

This task should improve visibility and no-fabrication UX without claiming production provider validation or building a full operational SLA platform.

## Requirements

### 1. Unified frontend trust model

- Add a small frontend normalization layer for data trust metadata instead of hand-writing status logic in each component.
- Normalize common fields from existing payloads: `status`, `freshness`, `data_mode`, `source`, `provider`, `requested_provider`, `effective_provider`, `as_of`, `generated_at`, `no_data_reason`, `availability`, `is_realtime`, `is_delayed`, `delay_minutes`, `freshness.cache_status`, and `session.status`.
- Support at least these display severities: ok/fresh, delayed, stale, mock/demo, degraded, no_data, unavailable, and unknown.
- Keep the model frontend-only for MVP unless a backend change is required to avoid data loss.

### 2. Shared UI component

- Add a reusable data-trust badge/summary component for compact and expanded display.
- It must show status in user-friendly Chinese labels, and expose details via visible text, title, or accessible description.
- It must distinguish provider/source/effective provider when available.
- It must not convert semantic error/success/destructive/bid/ask colors into market movement colors.

### 3. Homepage trust visibility

- Market overview rows must show status/freshness/source/provider/no-data reason when present.
- The black market ticker must not be a source-less quote strip; it should expose compact source/freshness/status details through accessible text or a visible compact badge.
- Homepage recommendations must stop using unconditional realtime wording unless payload explicitly supports realtime semantics.
- Recommendation diagnostics such as `provider_error` and `no_data` should be visible in the recommendation card when supplied.

### 4. Instrument-detail trust visibility

- The instrument detail page should show a page-level data-source summary for latest/bars/intraday/depth when available.
- Intraday chart states must show non-realtime, delayed, session, cache/freshness, and degraded/no-data reasons when present.
- K-line/daily bars and latest price displays must expose source/provider/status enough to avoid being mistaken for realtime quote data.
- Market depth should keep existing degraded/capability explanations and avoid Level-2 claims unless verified by payload metadata.

### 5. Reports and AI/research trust visibility

- Report list/detail surfaces must show `source_summary.source`, `price_source`, and `provider` when present.
- Report generation should pass the currently selected provider or clearly warn when the backend will use mock/default data.
- Assistant cards should keep citations/diagnostics and, when feasible in this task, surface the provider/source context before the answer.

### 6. Documentation and non-overclaiming

- Update manuals/runbooks when the UI changes so users understand source, provider, delayed/mock/degraded, and no-data states.
- Do not claim realtime, Level-2, production-grade fund-flow, or institutional SLA dashboards as complete in this task.

## Acceptance Criteria

- [x] A shared frontend trust normalizer and UI badge/summary are added with unit tests for fresh, stale, delayed, mock/demo, degraded, no_data, unavailable, and unknown inputs.
- [x] Homepage market overview rows display user-friendly trust metadata, including provider/source/freshness/status and reason when present.
- [x] Homepage ticker exposes provider/source/freshness/status in a compact or accessible form instead of naked price movement only.
- [x] Recommendation UI no longer unconditionally says realtime; provider/no_data/provider_error diagnostics are visible when supplied.
- [x] Instrument detail shows data-source/SLA summaries for latest/bars/intraday/depth and surfaces intraday freshness/session/delay/degraded reasons.
- [x] Reports list/detail display source/provider summaries, and report generation avoids silent mock usage or clearly labels it.
- [x] Existing hot-sector and market-depth degraded/mock/delayed semantics are preserved or improved without weakening no-fabrication behavior.
- [x] User/developer documentation is updated to explain the trust labels and remaining provider validation limits.
- [x] Focused frontend/backend tests and type checks pass for all touched surfaces.

## Out of Scope

- Production validation of live providers, entitlements, or paid Level-2 feeds.
- Building a full incident dashboard, uptime tracker, or provider SLA monitoring backend.
- WebSocket realtime streaming.
- Full professional screener, backtesting, portfolio risk, or workspace persistence features.
- Declaring professional-terminal parity.

## Current Evidence Summary

Good existing foundations:

- `packages/services/market_dashboard.py` already returns status, freshness, source, provider, requested/effective provider, generated_at, and no_data_reason for market overview items.
- `packages/services/market_data.py` returns rich intraday availability/freshness/session metadata and market-depth capability/degraded metadata.
- `packages/services/hot_sectors.py` already distinguishes live/delayed/mock/demo/none and provider capabilities.
- AI assistant contracts include citations, diagnostics, no-fabrication safety, provider/source context, and citation metadata.
- Reports store `source_summary` with source, price_source, provider, task_run_id, and citations.

Main gaps to fix:

- No shared frontend trust component/model.
- Homepage ticker and several price displays are source-less.
- Recommendations overuse realtime wording.
- Instrument intraday freshness/session/cache metadata is not surfaced.
- Reports source_summary is not visible to users.

## 2026-07-05 Implementation Update

The P0 frontend provider-trust MVP is implemented:

- Added `apps/web/lib/data-trust.ts` and `apps/web/components/data-trust-badge.tsx` with focused tests.
- Homepage market overview rows now show a trust summary; the black ticker exposes provider/source/status/freshness through accessible metadata.
- Smart recommendations now say “基于可用数据的技术信号” instead of unconditional realtime wording, and display provider/source/generated_at/diagnostics when supplied.
- Instrument detail surfaces latest-price and K-line trust summaries, and the intraday chart displays provider/source/availability/freshness/cache/session metadata in both available and degraded states.
- Reports list/detail surfaces show `source_summary`; report generation passes an explicit provider when supplied and warns when it will use the backend default.
- User and developer documentation now explain trust labels, report source summaries, and remaining provider validation limits.

Validation passed:

```powershell
npx vitest run 'apps/web/lib/data-trust.test.ts' 'apps/web/components/data-trust-badge.test.tsx' 'apps/web/components/market-ticker.test.tsx' 'apps/web/app/[locale]/page.test.tsx' 'apps/web/components/smart-recommendations.test.tsx' 'apps/web/components/intraday-price-chart.test.tsx' 'apps/web/app/[locale]/instruments/[symbol]/page.test.tsx' 'apps/web/app/[locale]/reports/page.test.tsx' 'apps/web/app/[locale]/reports/[reportId]/page.test.tsx' 'apps/web/components/generate-daily-report-button.test.tsx' 'apps/web/app/api/reports/[symbol]/daily/generate/route.test.ts' --reporter=dot
# 11 test files passed, 29 tests passed

npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0
# passed
```

This task does not implement a production provider incident/SLA backend, entitlement model, live-feed monitor, or professional terminal parity.

## Open Questions

No product question blocks MVP planning. The recommended implementation starts with the shared trust normalizer/component and then integrates it into homepage market overview/ticker plus recommendation wording, before expanding to instrument detail and reports.
