# Macro indicator online refresh status UI

## Goal

Turn the existing official macro refresh scripts into a browser-usable personal workflow. The user should be able to open Macro Research, see FRED and World Bank refresh coverage, run a dry-run check, and explicitly trigger a write refresh that stores audited local `MarketIndicatorObservation` rows.

The product value is practical macro information collection: reduce terminal-only steps, make source freshness visible, and feed AI summaries only values that have passed the existing local observation gate.

## Confirmed Facts

- This task was created after user approval on 2026-07-08.
- The app direction is a personal information aggregation and AI research assistant, not a professional trading or broker platform.
- Existing official refresh services already exist:
  - `refresh_fred_macro_indicators(...)` in `packages/services/market_indicators.py`;
  - `refresh_world_bank_macro_indicators(...)` in `packages/services/market_indicators.py`.
- Existing CLI entry points already exist:
  - `scripts/refresh_fred_macro_indicators.py`;
  - `scripts/refresh_world_bank_macro_indicators.py`.
- `apps/api/routers/market_indicators.py` currently exposes only seed preview/import endpoints, not official refresh endpoints.
- Next.js proxy examples already exist under `apps/web/app/api/market-indicators/seeds/*/route.ts`.
- Macro Research already renders a read-only official refresh status panel and command examples in `apps/web/app/[locale]/evidence/page.tsx`.
- Current Macro Research copy explicitly says "No web refresh action"; this task should change that if implementation proceeds.
- Existing backend spec `.trellis/spec/backend/market-indicator-seed-import-contract.md` defines official FRED and World Bank refresh contracts, including audit metadata and citation boundaries.
- FRED requires `FRED_API_KEY`; missing key must warn/fail safely and write nothing.
- World Bank Buffett refresh is public/no-secret and supports `buffett_indicator_us`, `buffett_indicator_cn`, and `buffett_indicator_hk`.
- `MarketIndicatorObservation` remains the AI-citable macro evidence gate. Source readiness rows, source capability rows, collection links, probe URLs, seed templates, and refresh diagnostics are guidance only.
- Product decision on 2026-07-08: the first browser-refresh MVP should allow both dry-run and explicit write refresh actions from Macro Research. This directly closes the terminal-only usability gap while keeping writes opt-in and visible.

## Requirements

### R1. Backend Official Refresh API

- Add explicit FastAPI mutation endpoints under `/market-indicators/official-refresh/*` or equivalent:
  - FRED refresh endpoint;
  - World Bank refresh endpoint.
- The endpoints must call the existing service functions instead of duplicating provider logic.
- Request payloads must support the safe subset already exposed by scripts:
  - FRED: series/group, optional start/end, `latest_only`, `dry_run`;
  - World Bank: target, optional start/end year, `latest_only`, `dry_run`.
- Response payloads must include:
  - provider/source type;
  - dry-run flag;
  - observations written or validated;
  - fetched/skipped counts;
  - affected indicator codes;
  - latest as-of date;
  - diagnostics;
  - cache-clear result for write runs.
- Dry-run must write no observations and must not clear market-overview cache as if data changed.
- Write runs must clear market-overview cache after successful observation writes.
- Missing FRED API key, provider errors, invalid date/year, and invalid target/group must return sanitized errors without exposing secrets or stack traces.

### R2. Next.js Same-Origin Proxies

- Add same-origin route handlers under `apps/web/app/api/market-indicators/official-refresh/*`.
- Proxies must forward method, body, cache policy, response status, and content type like the existing seed import/preview proxies.
- Browser components should call only the same-origin `/api/...` routes.

### R3. Macro Research UI Controls

- Replace the current read-only "No web refresh action" state with controlled refresh actions in Macro Research.
- Each provider panel should show:
  - current local coverage;
  - latest local as-of date;
  - dry-run action;
  - explicit write refresh action;
  - loading/success/failure result summary;
  - diagnostics and affected codes when available.
- The write action must be visually distinct from dry-run and must communicate that it stores audited local observations.
- Preserve command examples and runbook text as fallback/operator guidance.
- Keep UI localized in English and Chinese.

### R4. Source Freshness And Gaps

- Preserve existing macro favorite and Macro Research no-data/source-gap behavior.
- After a successful write refresh, the page should refresh/revalidate so updated local observations can appear without restarting the app.
- World Bank annual Buffett data must be described as annual/lagged public data, not realtime market data.
- Unsupported China monthly macro values such as `cn_m2_yoy` remain visible gaps unless an audited observation exists.

### R5. AI And Citation Safety

- AI summaries may cite only stored local observations and other existing allowed evidence types.
- Dry-run results, refresh diagnostics, source-readiness rows, seed templates, probe URLs, and collection guidance must not become AI citations.
- UI copy must stay research-oriented and must not provide buy/sell/hold calls, target prices, position sizing, or execution instructions.

### R6. Tests And Validation

- Add or update backend API tests for FRED and World Bank refresh endpoints, including dry-run/write behavior, cache clear, and sanitized errors.
- Add or update Next.js proxy tests for official-refresh endpoints.
- Add or update frontend tests for Macro Research controls and localized copy.
- Run focused backend tests, focused frontend tests, TypeScript if web files change, `npm run test:web -- --reporter=dot`, `git diff --check`, and Trellis validation.

## Acceptance Criteria

- [x] Backend exposes official refresh mutation endpoints for FRED and World Bank that reuse existing service refresh functions.
- [x] FRED dry-run validates through the service without writing observations.
- [x] FRED write refresh stores audited local observations when the provider succeeds and clears market-overview cache.
- [x] Missing or invalid FRED credentials/errors return sanitized non-secret responses and write nothing.
- [x] World Bank dry-run validates Buffett Indicator targets without writing observations.
- [x] World Bank write refresh supports US, mainland China, and Hong Kong Buffett Indicator observations and clears market-overview cache.
- [x] Next.js same-origin proxies forward refresh requests and preserve upstream statuses/payloads.
- [x] Macro Research UI provides localized dry-run and explicit write refresh controls for both providers.
- [x] Successful refresh result summaries show observations, fetched/skipped counts, affected codes, latest as-of date, and diagnostics.
- [x] Macro Research refresh success triggers page refresh/revalidation so current coverage can update.
- [x] Existing command/runbook guidance remains visible as fallback.
- [x] Source/readiness/guidance IDs and refresh diagnostics do not appear as AI citations.
- [x] Focused backend, frontend, proxy, TypeScript, web tests, `git diff --check`, and Trellis validation pass.

## Out Of Scope

- Scheduled/background refresh jobs.
- Production NBS/PBOC China monthly macro adapters.
- Paid/vendor macro integrations.
- Scraping public pages or storing raw document corpora.
- Authentication/authorization hardening beyond existing personal local app assumptions.
- Professional trading terminal features, broker workflows, realtime execution, Level-2 data, or direct investment advice.

## Open Questions

- None blocking.
