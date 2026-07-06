# Technical Design

## Architecture

Implement the Evidence Center as a thin product surface over existing evidence contracts.

Preferred first slice:

- Backend: reuse `GET /dashboard/market-overview` payload fields:
  - `macro_indicators.items`
  - `valuation_indicators.items`
  - `information_sources`
  - `dashboard_brief`
- Frontend: add a dedicated route under `apps/web/app/[locale]/evidence/page.tsx` or an equivalent first-class section if route wiring suggests a better local convention.
- Navigation: add one localized navigation item such as `Evidence Center`.
- UI: compose existing primitives and small local helpers; avoid adding a global state store.

This keeps the MVP low-risk because the data contracts are already tested through dashboard service/API/frontend coverage.

## Data Flow

```text
MarketIndicatorObservation
  -> packages/services/market_indicators.py
  -> packages/services/market_dashboard.py macro_indicators
  -> apps/web evidence route

Information source definitions + local evidence counts
  -> packages/services/information_sources.py
  -> packages/services/market_dashboard.py information_sources
  -> apps/web evidence route

Dashboard brief evidence/citations/diagnostics
  -> packages/services/market_dashboard.py dashboard_brief
  -> apps/web evidence route
```

## Contracts

### Indicator item

Use existing dashboard indicator fields:

- `code`
- `name`
- `region`
- `category`
- `status`
- `value`
- `unit`
- `as_of`
- `source`
- `components`
- `no_data_reason`

Derived UI state:

- `ai_citable`: true only when `status === "ok"` and `value`, `as_of`, and `source` are present.
- `metadata_present`: true when `components` includes at least one source key and one method/review key.
- `display_status`: preserve unknown backend status strings, but label known states clearly.

### Source readiness item

Use existing source fields:

- `id`
- `label`
- `category`
- `authority`
- `coverage`
- `status`
- `freshness_policy`
- `ai_usage`
- `next_action`
- `collection_note`
- `citation_policy`
- `collection_links`
- `seed_template`
- `evidence_count`
- `latest_as_of`

Do not convert `collection_links` or `seed_template` into citations.

### AI summary

Use existing dashboard brief fields:

- `sections`
- `citations`
- `diagnostics`
- `safety`
- `narrative.answer_markdown`
- `narrative.model`
- `narrative.context.source_mix`

If `narrative.model.used_llm` is false, display fallback state plainly. This is a product strength: it tells the user when AI did not generate the answer.

## UI Structure

Recommended first-screen order:

1. AI evidence summary and source-mix counts.
2. Macro/valuation indicator evidence table.
3. Source gaps and next actions.
4. Seed-template/source collection details.
5. Citation boundary and safety note.

This order matches the product goal: summary first, evidence next, then collection workflow.

## Compatibility

- Keep `GET /dashboard/market-overview` backward compatible.
- Do not remove the homepage macro/source sections in this slice unless the user explicitly asks for a layout simplification.
- Reuse existing `backendFetch`, `withProviderQuery`, translation files, and page-test patterns.
- Use route-local payload types unless a shared type already exists.

## Risks and Guardrails

- Risk: the UI may imply external links are evidence.
  - Guardrail: every source/template detail must show citation-boundary wording.
- Risk: no-data macro rows may look like valid zero values.
  - Guardrail: render absent values as unavailable/no audited observation, never `0`.
- Risk: adding another dashboard view duplicates complex homepage logic.
  - Guardrail: keep the route focused on evidence and source collection; do not copy unrelated market widgets.
- Risk: the task grows into a source-ingestion platform.
  - Guardrail: no new scraping, scheduling, licensed corpus storage, or document ingestion in this MVP.

## Rollback

The first slice should be additive. Rollback is removing the route/navigation item and docs if necessary; existing backend/dashboard contracts remain unchanged.
