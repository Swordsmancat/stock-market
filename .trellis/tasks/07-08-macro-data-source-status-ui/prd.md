# Macro data source status and refresh guidance UI

## Goal

Make the personal macro workflow self-explanatory from the homepage and Macro Research page. The user should be able to see whether official macro sources are configured, whether local observations are fresh enough to support AI summaries, and where to click next when a homepage macro favorite is missing or stale.

The feature should improve information aggregation and AI research readiness. It must not turn the app into a professional trading terminal or imply realtime trading signals.

## Confirmed Facts

- The current active direction is a personal information collection and AI summary/recommendation site, not a professional trading website.
- The previous task added browser dry-run and explicit write refresh buttons for:
  - FRED official macro observations;
  - World Bank Buffett Indicator observations.
- `packages/shared/config.py` exposes `fred_api_key`, `fred_api_base_url`, and `world_bank_api_base_url`.
- `packages/services/platform_settings.py` already exposes public configured flags for LLM and Tushare tokens, but it does not expose official macro source configuration/readiness.
- `packages/services/information_sources.py` already returns source readiness items with `status`, `freshness_policy`, `next_action`, `evidence_count`, `latest_as_of`, `coverage`, and citation boundaries.
- Macro Research already renders an official refresh panel in `apps/web/app/[locale]/evidence/page.tsx`.
- The homepage already renders favorite macro indicators from `platformSettings.favorite_macro_indicator_codes` in `apps/web/app/[locale]/page.tsx`.
- Existing source readiness and refresh diagnostics are guidance only. AI citations may come from stored local observations, stored reports/news, and reviewed citable notes, not from readiness rows or dry-run diagnostics.
- There is no existing persisted refresh-run history for official macro refresh actions. Current durable freshness comes from stored `MarketIndicatorObservation.as_of` and source readiness `latest_as_of`.
- Product decision on 2026-07-08: this MVP should not persist official refresh run history. Status should be derived from configuration, local observations, and source readiness.

## Requirements

### R1. Official Macro Source Status Contract

- Add a backend service/API payload that summarizes official macro source status for FRED and World Bank.
- The payload must include at least:
  - provider key (`fred`, `world_bank`);
  - display/source label;
  - configured/available status;
  - credential requirement and configured flag where applicable;
  - base URL or source URL metadata that is safe to show;
  - supported indicator codes;
  - latest local observation date;
  - evidence count;
  - freshness policy;
  - recommended next action;
  - citation boundary text.
- FRED must show `FRED_API_KEY` as required and whether it is configured without exposing the key.
- World Bank must show that no secret is required and that data is annual/lagged.
- The contract must be additive and must not alter market-overview citation behavior.

### R2. Macro Research Status/Guidance UI

- Macro Research should show source configuration/readiness near the existing official refresh controls.
- For each provider, the UI should make clear:
  - whether the provider can be refreshed from the browser now;
  - whether the missing blocker is configuration, no local observations, or source data lag;
  - which indicators the provider covers;
  - the latest local as-of date and evidence count;
  - that dry-run diagnostics and source readiness are not AI citations.
- The existing dry-run/write refresh controls and runbook text must remain available.
- UI text must be localized in English and Chinese.

### R3. Homepage Favorite Macro Guidance

- The homepage favorite macro indicator cards should guide the user to Macro Research when a favorite is missing or stale.
- Missing favorite cards should explain whether the likely action is:
  - configure FRED;
  - run FRED refresh;
  - run World Bank refresh;
  - review/manual-seed China-only values that do not yet have an audited adapter.
- Available favorite cards should keep showing value, as-of date, source, region, and category.
- Homepage copy must keep the research-only boundary and avoid trading recommendations.

### R4. Freshness Semantics

- Freshness should be derived from existing local observations and source readiness in this MVP.
- Official refresh run history must not be persisted in this slice.
- Do not fabricate a current value when an official source is lagged or unavailable.
- World Bank annual Buffett Indicator values must be described as annual/lagged context.
- FRED values should be described by cadence:
  - rates/spread: daily business-day source;
  - CPI/M2 YoY: monthly or source-release dependent.
- Staleness thresholds can be simple policy labels for this slice rather than a full release calendar.

### R5. Safety And Citation Boundaries

- No buy/sell/hold calls, target prices, position sizing, execution flows, or broker actions.
- No new AI citation source type.
- Source status, configuration flags, refresh diagnostics, source links, and runbook guidance must remain non-citable guidance.
- Only stored local observations can make macro values AI-citable.

### R6. Tests And Validation

- Add or update backend tests for the macro source status payload.
- Add or update API/proxy tests if a new route is exposed to the frontend.
- Add or update homepage and Macro Research tests for source status, missing favorite guidance, and localized copy.
- Run focused backend tests, focused frontend tests, TypeScript, full web tests, `git diff --check`, and Trellis validation.

## Acceptance Criteria

- [ ] Backend exposes an official macro source status payload for FRED and World Bank without leaking secrets.
- [ ] FRED status reports whether `FRED_API_KEY` is configured and identifies covered indicators.
- [ ] World Bank status reports no-secret availability, annual/lagged semantics, and covered Buffett Indicator regions.
- [ ] Macro Research displays provider configuration/readiness beside the refresh controls.
- [ ] Macro Research preserves dry-run/write controls, runbook fallback, and citation-boundary text.
- [ ] Homepage favorite macro cards show an actionable Macro Research/configuration path when values are missing.
- [ ] Homepage available favorite cards continue to show existing value/as-of/source information.
- [ ] Source status and refresh diagnostics are not added to AI citations.
- [ ] English and Chinese localization are updated together.
- [ ] Focused backend/frontend/proxy tests, TypeScript, full web tests, `git diff --check`, and Trellis validation pass.

## Out Of Scope

- Persisted refresh-run history.
- Scheduled/background macro refresh jobs.
- New China NBS/PBOC production adapters.
- A full macro release calendar.
- Paid/vendor integrations such as Trading Economics production API.
- Professional trading terminal features, realtime execution, direct investment advice, target prices, or broker workflows.
