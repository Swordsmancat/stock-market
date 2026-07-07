# Official macro indicator refresh for homepage favorites

## Goal

Turn the existing official macro refresh capability into a reliable personal-data workflow for the homepage macro favorites. The user should be able to refresh FRED-backed US macro indicators and World Bank-backed Buffett Indicator readings, then see audited values on the homepage and Macro Research page with clear source/as-of metadata.

The product value is practical information aggregation: the app should collect hard-to-find macro context from official/public sources, make gaps visible, and give AI summaries only evidence that has been stored as reviewed local observations.

## Confirmed Facts

- The app is a personal information aggregation and AI research cockpit, not a professional trading terminal.
- Homepage macro favorites are already settings-backed and default to:
  - `buffett_indicator_us`
  - `buffett_indicator_cn`
  - `buffett_indicator_hk`
  - `us_10y_yield`
  - `us_10y_2y_spread`
  - `us_cpi_yoy`
  - `us_m2_yoy`
  - `cn_m2_yoy`
- FRED provider support already exists in `packages/providers/fred_provider.py`.
- World Bank provider support already exists in `packages/providers/world_bank_provider.py`.
- FRED refresh service support already exists in `packages/services/market_indicators.py` through `refresh_fred_macro_indicators(...)`.
- World Bank Buffett Indicator refresh service support already exists in `packages/services/market_indicators.py` through `refresh_world_bank_macro_indicators(...)`.
- CLI entry points already exist:
  - `scripts/refresh_fred_macro_indicators.py`
  - `scripts/refresh_world_bank_macro_indicators.py`
- Config already exposes:
  - `FRED_API_KEY`
  - `FRED_API_BASE_URL`
  - `WORLD_BANK_API_BASE_URL`
- Backend spec already defines official refresh contracts in `.trellis/spec/backend/market-indicator-seed-import-contract.md`.
- Existing source-readiness and source-capability rows are collection guidance only. They must not become AI citations.
- `MarketIndicatorObservation` rows are the local audited evidence gate for dashboard and assistant citations.

## Requirements

### R1. Verify Existing Official Refresh Paths

- Run focused provider, service, and script tests for FRED and World Bank refresh.
- Confirm dry-run behavior writes no observations.
- Confirm missing FRED API key prints a sanitized warning and writes nothing.
- Confirm World Bank refresh works without secrets and skips missing/null/invalid rows.
- Confirm stored observations preserve source and method metadata required by the audited seed contract.

### R2. Fill Product Gaps Around Refresh Usability

- Add a concise runbook for manual refresh operation.
- Add a small read-only status/guidance UI in the macro workflow so the user can discover how refresh works and understand which indicators still need data.
- Do not add a web-triggered refresh button or mutation endpoint in this task.
- Keep refresh opt-in. Do not add background scheduler, automatic scraping, broker workflow, or realtime terminal behavior.

### R3. Homepage Macro Data Closure

- After refresh/import, homepage macro favorites should show `status="ok"`, value, as-of date, source, and region/category metadata from local observations.
- Missing data should continue to show source-gap wording instead of zero or fabricated values.
- US and mainland China Buffett Indicator readings must remain market-wide regional valuation indicators, not individual-stock metrics.
- `cn_m2_yoy` may remain a documented gap if no official adapter is implemented in this task.

### R4. Citation And AI Safety Boundaries

- Dashboard brief, saved research briefs, and market assistant may cite only stored local observation IDs and other allowed evidence IDs.
- FRED/World Bank source IDs, readiness rows, probe URLs, seed templates, and collection links remain guidance only until local observations exist.
- AI output must remain research-summary/risk-context oriented and must not emit buy/sell/hold calls, target prices, position sizing, or execution instructions.

### R5. Documentation And Operator Workflow

- Add or update a concise manual for refreshing macro indicators:
  - prerequisites and environment variables;
  - FRED command examples;
  - World Bank command examples;
  - dry-run examples;
  - how to verify the homepage/Macro Research results;
  - what remains manual or unavailable.
- The manual should make clear that values become AI-citable only after refresh stores audited observations locally.

## Acceptance Criteria

- [ ] FRED provider/service/script focused tests pass.
- [ ] World Bank provider/service/script focused tests pass.
- [ ] A dry-run refresh path is verified for both providers without leaving observations behind.
- [ ] Missing FRED API key produces a sanitized warning and no network request.
- [ ] World Bank Buffett refresh supports `buffett_indicator_us`, `buffett_indicator_cn`, and `buffett_indicator_hk`.
- [ ] Stored official-source observations include provider, source URL or source series/indicator ID, retrieved timestamp, and methodology/calculation metadata.
- [ ] Homepage macro favorites can show refreshed official observations with value/source/as-of metadata.
- [ ] Missing `cn_m2_yoy` or other unsupported China macro values are documented as source gaps, not fabricated values.
- [ ] Source-readiness IDs, source-capability IDs, collection links, probe URLs, and seed templates do not appear in dashboard/assistant/saved-brief citation lists.
- [ ] User manual/runbook explains how to refresh official macro indicators and verify the result.
- [ ] A read-only status/guidance UI explains the manual refresh workflow without triggering backend refresh jobs.
- [ ] Validation includes focused backend tests, relevant frontend tests if UI copy changes, TypeScript when web files change, `git diff --check`, and Trellis task validation.

## Out Of Scope

- Production NBS/PBOC China macro adapter.
- Scheduled/background macro refresh jobs.
- Scraping public websites or storing raw document corpora.
- Paid/vendor macro data integrations.
- Professional trading terminal features, realtime quotes, Level-2 data, broker execution, or alert automation.
- Direct investment advice, buy/sell/hold recommendations, target prices, position sizing, or execution instructions.
