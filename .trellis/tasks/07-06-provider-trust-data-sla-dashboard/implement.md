# Provider Trust and Data SLA Dashboard - Implementation Plan

## Current phase

Implemented and locally verified. The task remains in Trellis until final review/finish flow, but the P0 frontend provider-trust MVP scope is code-complete.

## Evidence gathered

Read-only audit found existing trust metadata in:

- dashboard market overview service/API;
- daily bars, latest quote, intraday, and market depth services;
- hot sectors service and component;
- AI assistant citations/diagnostics;
- generated reports `source_summary`;
- recommendation diagnostics.

It also found missing or weak frontend trust presentation in:

- homepage ticker;
- market overview status/source/freshness details;
- recommendations realtime wording and diagnostics;
- instrument latest/bars/intraday trust summaries;
- report list/detail source summaries.

## Ordered implementation checklist

### 1. Shared trust model and component

- [x] Add `apps/web/lib/data-trust.ts` with a pure normalizer.
- [x] Add tests for fresh, stale, delayed, mock/demo, degraded, no_data, unavailable, and unknown states.
- [x] Add `DataTrustBadge` / `DataTrustSummary` component.
- [x] Add component tests for compact and summary modes.

### 2. Homepage market overview and ticker

- [x] Extend relevant frontend item types to preserve `source`, `provider`, `requested_provider`, `effective_provider`, `generated_at`, `freshness`, `status`, and `no_data_reason` where available.
- [x] Render trust summary in `MarketOverviewClient` status/source column.
- [x] Add compact accessible source/status/freshness indication to `MarketTicker`.
- [x] Update homepage tests to cover visible or accessible trust metadata.

### 3. Recommendations no-overclaim

- [x] Replace unconditional realtime wording with “technical signals based on available data” wording.
- [x] Surface generated_at and diagnostics where present.
- [x] Show provider_error/no_data diagnostics in the recommendation card.
- [x] Add/update tests proving realtime is not claimed without supporting payload metadata.

### 4. Instrument detail and intraday

- [x] Extend `InstrumentIntradayPayload` type to include backend `freshness` and `session` fields.
- [x] Show page-level source/provider summary in `InstrumentDetailClient`.
- [x] Show latest/bars source/provider/status near price/K-line sections.
- [x] Show intraday non-realtime/delayed/cache/session/no-data/degraded details in `IntradayPriceChart`.
- [x] Add/update page and component tests.

### 5. Reports source summary

- [x] Show report `source_summary` in report list and detail pages.
- [x] Ensure report generation either passes provider explicitly or clearly labels mock/default provider usage.
- [x] Add/update reports page/detail/generation tests.

### 6. Documentation

- [x] Update `docs/manual/user-guide.md` with trust labels and examples.
- [x] Update `docs/runbooks/developer-maintenance.md` or README if provider validation/SLA limitations change.
- [x] Update parent and professional-dashboard Trellis notes with final status.

## Implementation summary

- Shared trust layer: `apps/web/lib/data-trust.ts`, `apps/web/components/data-trust-badge.tsx`.
- Homepage: `market-overview-client.tsx`, `market-ticker.tsx`, and homepage payload mapping now preserve/display provider trust fields.
- Recommendations: `smart-recommendations.tsx` no longer uses unconditional realtime language and displays diagnostics/provider/source metadata.
- Instrument detail: latest, K-line, and intraday surfaces expose source/provider/freshness/session/cache semantics.
- Reports: list/detail pages show `source_summary`; generation warns when no explicit provider is passed.
- Documentation: user guide, developer runbook, README, parent task, and professional-dashboard notes were updated.

## Validation evidence

```powershell
npx vitest run 'apps/web/lib/data-trust.test.ts' 'apps/web/components/data-trust-badge.test.tsx' 'apps/web/components/market-ticker.test.tsx' 'apps/web/app/[locale]/page.test.tsx' 'apps/web/components/smart-recommendations.test.tsx' 'apps/web/components/intraday-price-chart.test.tsx' 'apps/web/app/[locale]/instruments/[symbol]/page.test.tsx' 'apps/web/app/[locale]/reports/page.test.tsx' 'apps/web/app/[locale]/reports/[reportId]/page.test.tsx' 'apps/web/components/generate-daily-report-button.test.tsx' 'apps/web/app/api/reports/[symbol]/daily/generate/route.test.ts' --reporter=dot
# 11 test files passed, 29 tests passed

npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0
# passed
```

## Validation plan

Focused frontend tests:

```powershell
npx vitest run "apps/web/lib/data-trust.test.ts" "apps/web/components/data-trust-badge.test.tsx" "apps/web/components/market-ticker.test.tsx" "apps/web/app/[locale]/page.test.tsx" "apps/web/components/intraday-price-chart.test.tsx" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx" --reporter=dot
```

Additional likely tests after reports/recommendations changes:

```powershell
npx vitest run "apps/web/components/smart-recommendations.test.tsx" "apps/web/app/[locale]/reports/page.test.tsx" "apps/web/app/[locale]/reports/[reportId]/page.test.tsx" "apps/web/components/generate-daily-report-button.test.tsx" --reporter=dot
```

Backend/API tests if backend or proxy payloads change:

```powershell
python -m pytest tests/api/test_dashboard_api.py tests/api/test_market_depth_api.py tests/api/test_recommendations_api.py tests/api/test_reports_api.py tests/api/test_assistant_api.py tests/services/test_hot_sectors_service.py tests/ai/test_market_assistant.py tests/services/test_data_quality.py -q
```

General checks:

```powershell
npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0
npm run test:web -- --reporter=dot
git diff --check
```

## Risk points

- The working tree is already dirty from several Trellis tasks; do not revert unrelated changes.
- Some existing fields are snake_case and raw payloads are loosely typed. Keep type additions additive and explicit.
- Do not turn missing metadata into `fresh` or `live` defaults.
- Avoid expanding this task into full provider incident/SLA backend infrastructure.

## Recommended start slice

Start with Slice 1 plus the smallest homepage integration: `data-trust.ts`, `DataTrustBadge`, market overview row display, and ticker accessible trust metadata. This gives the rest of the task a stable shared foundation before touching reports and instrument detail.
