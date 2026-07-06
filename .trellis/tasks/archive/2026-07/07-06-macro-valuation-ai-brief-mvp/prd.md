# Macro Valuation Indicators and AI Daily Brief MVP

## Goal

Implement the first approved slice of the personal investment cockpit: expand the existing Buffett Indicator foundation into a broader macro/valuation indicator board, preserve auditable source/no-data behavior, add a dashboard-level daily brief, and update product positioning docs so the site emphasizes information aggregation and AI interpretation.

## Parent Dependency

Parent task: `.trellis/tasks/07-06-personal-investment-info-ai-summary`.

The parent establishes the product direction: personal information aggregation, macro indicator collection, hard-to-find source gathering, and AI summary/recommendation. This child task is the P0 implementation slice and should not pull in P1/P2 notebook, document-ingestion, or terminal-grade features.

## Confirmed Repository Facts

- `packages/services/market_indicators.py` already defines Buffett Indicator entries for CN/HK/US and returns explicit `no_data` until audited observations exist.
- `packages/domain/models.py` already has `MarketIndicator` and `MarketIndicatorObservation` tables with source and component JSON fields.
- `packages/services/market_dashboard.py` includes `valuation_indicators` in the dashboard payload.
- `apps/web/app/[locale]/page.tsx` already renders valuation indicator cards from the market overview payload.
- `packages/services/market_assistant.py` already has the desired AI safety pattern: evidence citations, diagnostics, unknown-citation validation, and deterministic fallback.
- README and `docs/manual/user-guide.md` previously mixed research-dashboard language with professional-terminal comparison and have now been reframed around personal information aggregation, macro/valuation watchpoints, and AI summaries.

## Requirements

### R1. Macro/Valuation Indicator Registry

- Extend the existing indicator definitions beyond Buffett Indicator.
- P0 definitions should include a curated set, not every possible macro series:
  - `buffett_indicator_cn`, `buffett_indicator_hk`, `buffett_indicator_us`.
  - US 10Y yield.
  - US 2Y yield.
  - US 10Y minus 2Y spread.
  - US CPI YoY.
  - US M2 YoY or latest M2 level/growth.
  - optional CN M2 or credit proxy if the data source is already easy to represent as a no-data definition.
- Keep definitions available even when no observations have been seeded.
- Group indicators by category: valuation, rates, inflation, liquidity, and risk/stock-bond attractiveness where implemented.

### R2. Auditable Observation Contract

- Every populated observation must expose:
  - code
  - name
  - category
  - region
  - unit
  - status
  - value
  - as-of date
  - source
  - components/method metadata
  - no-data reason when unavailable
- Missing data must render as no-data, not zero.
- Seeded sample observations, if added, must be clearly marked as audited/demo seed data and must not pretend to be live macro data.

### R3. Dashboard Daily Brief MVP

- Add a dashboard-level deterministic brief before LLM expansion.
- The brief should summarize:
  - available macro/valuation signals.
  - unavailable macro/valuation signals.
  - watchlist or followed-instrument freshness.
  - latest report/news availability where already loaded.
  - next research actions.
- It should be structured as "what changed", "why it matters", "what to watch next", and "data gaps".
- The brief must not issue buy/sell/hold instructions.

### R4. AI-Ready Contract

- Shape the brief/evidence payload so a later P1 LLM dashboard brief can reuse it.
- Include stable evidence IDs, source labels, excerpts, and diagnostics where practical.
- Do not introduce an LLM call in P0 unless it can reuse the existing assistant citation validation safely and remain small.

### R5. Frontend Positioning

- Reframe the homepage first viewport or summary copy around:
  - personal information aggregation.
  - macro and valuation watchpoints.
  - AI summary/research lead generation.
- Keep dense finance UI where useful, but stop presenting terminal parity as the goal.
- Macro/valuation indicators should show source/freshness/no-data status near the value.

### R6. Documentation

- Update `README.md` key feature/status language.
- Update `docs/manual/user-guide.md` so it explains the macro/valuation board, daily brief, AI boundaries, and revised professional comparison.
- Do not claim production live macro feeds unless implemented and verified.

## Out of Scope

- Full official API ingestion for every macro series.
- P1 citation-aware LLM dashboard brief.
- Document search over filings/transcripts/research.
- Personal notebook workflow.
- Backtesting, Level-2, live order flow, broker workflows, or professional terminal parity.

## Acceptance Criteria

- [x] Indicator definitions include the approved P0 macro/valuation set and keep explicit no-data states.
- [x] Service tests cover definitions, no-data payloads, and at least one auditable observation example.
- [x] Dashboard payload and UI expose grouped macro/valuation indicators with source/as-of/no-data information.
- [x] A dashboard-level deterministic daily brief is available and rendered in the main dashboard.
- [x] Brief output includes research-safe sections, report/news availability, citations, diagnostics, and avoids investment-advice language.
- [x] README and user manual are reframed toward personal information aggregation and AI summaries.
- [x] Validation commands in `implement.md` pass or failures are documented before close.

## Completion Notes

- P0 implementation completed on 2026-07-06.
- Professional-site comparison research is recorded in `research/professional-site-comparison.md`.
- Known follow-up work remains P1/P2: official macro source adapters, citation-aware LLM dashboard brief, brief history, personal research notebook, and legal/source-policy registry for hard-to-find information.

## Open Questions

No blocking product question remains. The user approved this slice on 2026-07-06.
