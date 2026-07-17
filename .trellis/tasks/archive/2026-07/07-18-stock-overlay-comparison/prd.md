# Add stock and overlay comparison workflow

## Goal

Turn the existing buried comparison card into a first-class personal stock
comparison workflow where the user can choose two to four A-share stocks,
compare normalized stored-price performance, and inspect returns, volatility,
and correlations without triggering a provider request.

## Background

The repository already contains `ComparisonTool` and `comparison-utils` with a
normalized line chart, interval summaries, correlation matrix, and text export.
Today the Instruments page automatically supplies only the first eight rows of
the current instrument page and fetches their bars through the general
market-data path. That is hard to discover, does not support arbitrary stock
selection, and can fall through to a provider during a normal page read.

This child merges the reference sidebar's Stock Comparison and Overlay
Comparison into one routed workflow. It reuses the existing calculations and
keeps Instruments as the owning navigation destination.

## Requirements

- Add a read-only `GET /market-comparison` endpoint for active CN stocks.
- Accept an ordered, deduplicated set of zero to four symbols, a bounded period
  of `1m|3m|6m|1y`, and an optional bounded search query.
- Search only stored active CN stocks. Do not use the existing seed fallback
  when PostgreSQL is empty or unavailable.
- Load only stored daily bars. Page load and endpoint reads must not call a
  provider, crawler, ingestion, backfill, shortlist, AI, or trading action.
- For each selected stock, choose one deterministic coherent
  `provider + adjustment` series by row count with a lexical tie-break. Never
  splice incompatible adjustment bases within one comparison series.
- Anchor the period to the latest stored selected-stock date, expose each
  series' provenance and date coverage, and compute the exact shared-date count.
- Return explicit states for empty selection, insufficient selection, missing
  symbols, and fewer than two comparable shared dates. Never fabricate rows or
  silently replace an unavailable requested symbol.
- Add `/[locale]/instruments/compare` as the single comparison workspace.
- Let the user search stored stocks, add/remove symbols through URL state, and
  switch periods without client-only hidden state. Enforce two to four selected
  stocks before rendering analysis.
- Reuse the existing overlay chart, return/volatility table, correlation
  matrix, and report export after aligning every selected series to the same
  shared dates and the same first shared baseline date.
- Move comparison ownership out of the general Instruments page so opening the
  list no longer loads up to eight comparison bar series. Add a compact
  `Compare stocks` action that opens the dedicated workflow.
- Keep the existing sidebar and five-item mobile navigation unchanged. Add only
  localized breadcrumb/page/action text in Chinese and English.
- Preserve the research-only boundary and do not add recommendations, target
  prices, portfolio weights, orders, brokers, or automated trading.

## Acceptance Criteria

- [ ] Service tests prove request normalization, database-only search, exact
      symbol identity, coherent per-stock series selection, period anchoring,
      shared-date counts, numeric safety, stable order, and explicit states.
- [ ] API tests prove query validation and database-session delegation.
- [ ] Comparison utility tests prove all selected series normalize from the
      first exact shared date and correlations use only aligned observations.
- [ ] The dedicated page renders search/add/remove controls, period controls,
      selected provenance, overlay chart, summary metrics, correlation matrix,
      empty/insufficient/no-data/error states, and exact detail links.
- [ ] The Instruments page links to comparison but performs no comparison-bar
      request on ordinary list load.
- [ ] Page and API reads issue GET requests only and cannot reach provider or
      mutation paths.
- [ ] Desktop and `390x844` browser acceptance show no incoherent overlap or
      page-level horizontal overflow.
- [ ] Focused and full backend/frontend tests, Ruff, TypeScript, locale JSON,
      Trellis validation, and scoped `git diff --check` pass.

## Out of Scope

- ETFs, indexes, funds, futures, Hong Kong/US markets, intraday overlays, live
  quotes, streaming, provider refresh, saved comparison portfolios, or sharing.
- Fundamental side-by-side matrices, AI-written comparison conclusions, or
  automatic selection of comparison candidates.
- New database tables or persistence of comparison selections/reports.
