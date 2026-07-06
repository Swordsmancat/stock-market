# Design: Personal Investment Information Aggregation and AI Summary Platform

## Product Boundary

The platform should behave like a personal research cockpit:

1. Collect auditable facts from market, macro, valuation, news, and user-curated sources.
2. Normalize those facts into source-aware payloads.
3. Show freshness, source, method, and missing-data state directly in the UI.
4. Ask AI to summarize and recommend research follow-ups from those facts.

It should not behave like a trading terminal. Existing intraday, depth, charting, sector, and recommendation modules are supporting evidence sources, not the core product promise.

## Current Architecture To Reuse

- `packages/domain/models.py`
  - `MarketIndicator` and `MarketIndicatorObservation` already model source-aware macro/valuation observations.
  - `GeneratedReport`, `NewsArticle`, `SentimentSignal`, watchlist, portfolio, alert, and bar models provide existing evidence stores.
- `packages/services/market_indicators.py`
  - Seeds Buffett Indicator definitions and deliberately returns explicit no-data when observations are not audited.
  - This should become the foundation for a broader indicator registry.
- `packages/services/market_dashboard.py`
  - Aggregates followed instruments, indices, valuation indicators, and diagnostics into the dashboard payload.
- `packages/services/market_assistant.py`
  - Builds citation-aware assistant context with no-data diagnostics and deterministic fallback.
- `apps/web/app/[locale]/page.tsx`
  - Already renders valuation indicators, dashboard freshness, reports, recommendations, news, and watchlist state.

## Target Data Model

Keep the existing `MarketIndicator` / `MarketIndicatorObservation` structure and extend it by convention before adding new tables:

- `code`: stable identifier, e.g. `buffett_indicator_us`, `us_10y_yield`, `cn_m2_growth`.
- `category`: `valuation`, `rates`, `inflation`, `liquidity`, `growth`, `sentiment`, `risk`.
- `region`: `US`, `CN`, `HK`, `GLOBAL`, or source-specific region.
- `unit`: `percent`, `index`, `ratio`, `currency`, `basis_points`, `number`.
- `description`: user-readable method and meaning.
- observation `source`: source note or provider ID.
- observation `components_json`: raw components, formula, source URLs/IDs, retrieval metadata, and method caveats.

If this becomes too large, add a follow-up migration for:

- `source_url`
- `retrieved_at`
- `methodology_json`
- `freshness_policy_json`
- `confidence/status`

## Source Strategy

Use a provider ladder:

1. Official/public APIs where available, such as FRED for US macro series and World Bank/OECD-style official macro data.
2. Existing market data providers for market-cap/index components when terms permit.
3. User-curated seed files for indicators where source components need manual review.
4. Licensed or user-provided documents for filings/transcripts/research.
5. Link-and-summary workflows where full-text storage is not appropriate.

All source adapters must preserve:

- `source`
- `as_of`
- `retrieved_at` when available
- source URL or source series ID
- method note
- components used in calculation
- freshness/no-data reason

## Macro Indicator MVP

P0 should extend the current Buffett Indicator foundation instead of introducing a separate macro subsystem.

Initial groups:

- Valuation:
  - Buffett Indicator CN/HK/US.
  - index valuation percentile if auditable.
- Rates:
  - 10Y yield.
  - 2Y yield.
  - yield curve spread.
- Inflation:
  - CPI YoY.
  - PPI YoY where useful.
- Liquidity:
  - M2 growth.
  - credit/social financing proxy where sourceable.
- Stock-bond attractiveness:
  - earnings yield vs bond yield or equity risk premium, only if components are explicit.

## AI Summary Flow

Add a dashboard-level AI summary service after macro payloads are reliable:

1. Collect evidence:
   - latest macro/valuation indicators.
   - watchlist movement and freshness.
   - latest generated reports.
   - recent news sentiment/events.
   - hot-sector provider metadata.
   - current data gaps.
2. Rank and dedupe evidence.
3. Build a prompt with required sections:
   - what changed.
   - why it matters.
   - what to watch next.
   - risk notes.
   - missing data.
   - citations.
4. Validate citations against retrieved evidence.
5. Fall back to deterministic summary if LLM or citations fail.

This should reuse the citation validation and fallback pattern in `packages/services/market_assistant.py`.

## UI Direction

Revise the dashboard hierarchy:

1. AI daily/weekly summary and key watch items.
2. Macro and valuation indicator board.
3. Watchlist movement and freshness.
4. News/events and generated report digest.
5. Supporting charts, recommendations, sectors, portfolio, and tasks.

Use professional-finance density only where it helps scanning. Avoid making terminal-style widgets the product centerpiece.

## Documentation Direction

After scope approval, update:

- `README.md`
  - Product description.
  - Key features.
  - Phase status table.
- `docs/manual/user-guide.md`
  - Current behavior.
  - Macro indicator state.
  - AI summary boundaries.
  - Reframed professional comparison.
- `docs/runbooks/developer-maintenance.md`
  - Source freshness, no-data policy, indicator seeding, and provider validation.

## Risks

- Macro series licensing and redistribution can be non-obvious.
- Buffett Indicator components are easy to mislead with stale or mismatched market-cap/GDP dates.
- AI summaries can overstate conclusions unless citations and data gaps are prominent.
- Too many indicators can create noise; start with a curated set and clear categories.

## Rollback

Planning/doc-only changes can be rolled back by removing this task's planning artifacts. Future implementation slices should keep source adapters and UI panels behind explicit no-data/degraded states so incomplete source coverage does not break the dashboard.
