# Macro Valuation Evidence Center

## Goal

Build a dedicated Evidence Center for personal macro and valuation research. The feature should make audited local observations, source readiness, manual collection templates, freshness status, and AI-citable evidence easy to inspect from one place.

This is not a trading terminal feature. It should strengthen the product's current direction: personal information aggregation, hard-to-find source collection guidance, macro/valuation evidence tracking, and AI summaries that explain what is known, what is missing, and what to review next.

## Background

The repository already has the core evidence foundations:

- `packages/services/market_indicators.py` defines macro and valuation indicators for Buffett Indicator, US rates, CPI YoY, US M2 YoY, and China M2 YoY.
- `scripts/import_market_indicator_seeds.py` imports audited JSON/CSV observations only when source and method metadata are present.
- `packages/providers/fred_provider.py` and `scripts/refresh_fred_macro_indicators.py` provide an opt-in official FRED refresh path for US rates, CPI, and M2.
- `packages/services/information_sources.py` exposes source readiness, collection links, seed templates, evidence counts, and citation boundaries.
- `packages/services/market_dashboard.py` includes `macro_indicators`, `information_sources`, and citation-aware `dashboard_brief.narrative`.
- `apps/web/app/[locale]/page.tsx` already renders macro indicators, source-readiness guidance, seed templates, and AI brief context on the homepage.

The gap is product shape, not raw capability. These pieces are currently embedded in a busy homepage. The user needs a focused research workspace that answers:

- Which macro and valuation observations are locally stored and AI-citable?
- Which items are source links or templates only?
- Which indicators are stale, missing, or waiting for manual review?
- What source or command should be used next?
- What did AI summarize from actual evidence, and what did it mark as a gap?

## Requirements

### 1. Dedicated Evidence Center entry

- Add a clear Evidence Center route or first-class dashboard section focused on macro/valuation information collection.
- The first viewport should show the current evidence state rather than a marketing page.
- The view should prioritize AI summary, key macro/valuation indicators, source gaps, and next collection actions.
- Navigation should make the feature discoverable without making the app look like a professional trading terminal.

### 2. Macro and valuation evidence table

- Show all current `MACRO_INDICATOR_CODES`:
  - `buffett_indicator_cn`
  - `buffett_indicator_hk`
  - `buffett_indicator_us`
  - `us_10y_yield`
  - `us_2y_yield`
  - `us_10y_2y_spread`
  - `us_cpi_yoy`
  - `us_m2_yoy`
  - `cn_m2_yoy`
- For each item, show code, name, category, region, value, unit, as-of date, source, method/source metadata presence, status, and no-data reason.
- Distinguish at minimum:
  - local audited observation exists and is AI-citable;
  - source is known but needs an adapter;
  - manual seed is required;
  - no local evidence exists;
  - future source only.
- Missing values must remain missing; they must not be rendered as zero.

### 3. Source readiness and collection workflow

- Reuse `information_sources` payload fields instead of inventing an unrelated source model.
- Show each source's status, authority, coverage, freshness policy, AI usage, citation policy, evidence count, latest as-of, collection links, and next action.
- Seed templates should be visible for relevant sources, including required fields, JSON/CSV placeholders, review checklist, warnings, import command, and citation boundary.
- Collection links and seed templates must remain guidance only. They must not appear as AI citations until reviewed observations are imported.

### 4. AI evidence summary

- Surface the existing dashboard brief/narrative context in a way that emphasizes evidence and gaps:
  - what changed;
  - why it matters;
  - what to watch next;
  - source and data gaps;
  - citation counts by macro/report/news;
  - model/fallback status.
- The UI must make citation boundaries visible: AI can cite stored observations, generated reports, and stored news, but not unimported source links or seed templates.
- The summary must preserve the no-investment-advice boundary and avoid buy/sell/hold, target-price, position-sizing, or execution language.

### 5. Freshness and review guidance

- Display freshness policy text from the existing source registry.
- Where possible in this slice, classify visible items into simple user-facing states such as `fresh`, `stale`, `no_data`, `needs_adapter`, `needs_manual_seed`, and `future`.
- If freshness thresholds are not yet formalized per indicator, show the source policy and as-of date rather than pretending an exact SLA exists.
- The feature should produce a clear next action for missing or stale items.

### 6. Documentation

- Update the user manual to describe the Evidence Center workflow and boundaries.
- Update developer maintenance docs with focused validation commands for this feature.
- Do not overclaim automatic ingestion, licensed document storage, realtime macro feeds, or professional-terminal parity.

## Acceptance Criteria

- [ ] A user can open a dedicated Evidence Center route or equivalent first-class surface for macro/valuation evidence.
- [ ] The view lists all configured macro/valuation indicator codes with local observation status, value/as-of/source when available, and explicit no-data messaging when absent.
- [ ] The view shows whether each item is AI-citable, collection guidance only, needs adapter, needs manual seed, no-data, or future scope.
- [ ] Source readiness items display collection links, citation policy, next action, seed-template previews, import command, warnings, and review checklist where available.
- [ ] The AI evidence summary shows answer/fallback state, source mix, citations, diagnostics, and source gaps without citing source-readiness links or templates as evidence.
- [ ] Existing homepage dashboard behavior remains backward compatible; old API payload fields are not removed.
- [ ] Tests cover the new route/surface, indicator status rendering, source-template rendering, citation-boundary text, and no-data behavior.
- [ ] Documentation is updated to describe the Evidence Center and validation commands.
- [ ] Full focused validation passes before implementation is reported complete.

## Out of Scope

- Broker execution, trading advice, order routing, position sizing, or buy/sell/hold recommendations.
- Professional terminal parity, Level-2/order-flow features, or realtime low-latency market data.
- Unauthorized scraping, hidden crawlers, or storage of licensed full-text research corpora.
- Automatic scheduled macro refresh jobs.
- New official source adapters beyond reusing the existing FRED adapter and manual seed flow.
- A complete document/filing/transcript ingestion platform.

## Open Questions

No blocking product question remains for MVP planning. The recommended first slice is a dedicated Evidence Center route that reuses the existing market-overview payload, information-source registry, macro indicator payloads, and dashboard brief narrative.
