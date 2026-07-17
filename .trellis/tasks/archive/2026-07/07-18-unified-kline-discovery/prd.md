# Unify stock ETF and index K-line access

## Goal

Provide one compact, database-only K-line workspace for stored stocks, ETFs,
and indexes so the reference sidebar's three K-line destinations become one
useful personal-research workflow instead of three duplicate pages.

## Background

The current instrument list exposes market and text filters but not asset type.
It also loads each visible symbol through the general latest-market-data path,
which can reach a provider. The stock detail page remains valuable for the
full stock workflow, but it also loads intraday, depth, fundamentals, news, and
reports that are not appropriate as the default ETF/index discovery surface.

This child adds a focused stored K-line workspace under Instruments. It reuses
the existing candlestick chart and exact instrument detail routes, while
keeping page reads separate from refresh, ingestion, AI, and trading actions.

## Requirements

- Add one read-only API projection for active stored instruments with asset
  type `stock`, `etf`, or `index`.
- Accept URL-safe filters for bounded search text, asset type, exact selected
  symbol and market, and period `1m|3m|6m|1y`.
- Search the database only. Never use the seed fallback when storage is empty
  or unavailable, and never silently substitute another instrument when an
  exact symbol/market pair is missing.
- Return a bounded catalog with asset type, market, exchange, currency, latest
  stored bar date, whether a coherent K-line series is available, stable
  filtered totals, offset pagination, and `has_more`.
- For a selected instrument, choose one deterministic coherent
  `provider + adjustment` daily-bar cohort by row count with a lexical
  tie-break. Never splice incompatible adjustment bases.
- Anchor the selected period to the latest stored date in that cohort and
  return finite OHLCV rows, provenance, date coverage, and explicit
  `empty|not_found|no_data|ready` states.
- Add `/[locale]/instruments/kline` as the unified workspace. Keep search,
  type, symbol, market, and period in the URL with GET-only forms and links.
- Render clear stock/ETF/index labels, selected identity and provenance, the
  existing candlestick chart, explicit empty/error states, and an exact link
  to the full instrument detail page.
- Add a compact K-line action to the existing Instruments page. Keep stock
  comparison separate, make Global Search use the same stored multi-asset
  catalog, and preserve the sidebar and five-item mobile nav.
- Opening or navigating the workspace must not call a provider, crawler,
  ingestion, backfill, shortlist, assistant, portfolio mutation, or trading
  endpoint.
- Preserve the research-only boundary: no recommendations, targets, position
  sizing, orders, brokers, or automated trading.

## Acceptance Criteria

- [ ] Service tests prove normalization, database-only catalog search, exact
      identity, supported asset types, coherent cohort selection, period
      anchoring, numeric safety, stable ordering, and every explicit state.
- [ ] API tests prove query validation and database-session delegation.
- [ ] The page renders catalog/type/search controls, selected identity,
      provenance, period controls, chart, detail link, and empty/error states.
- [ ] The Instruments page links to the workspace and ordinary list reads no
      longer issue one provider-capable latest request per visible row.
- [ ] Page and API reads issue GET requests only and cannot reach provider or
      mutation paths.
- [ ] Desktop and `390x844` acceptance show no incoherent overlap or page-level
      horizontal overflow, and a selected stored series renders a nonblank
      chart.
- [ ] Focused and full backend/frontend tests, Ruff, TypeScript, locale JSON,
      Trellis validation, and scoped `git diff --check` pass.

## Out of Scope

- Provider refresh, ingestion, backfill, or automatic repair of missing data.
- Intraday, market depth, streaming, futures, FX, or non-daily timeframes.
- ETF holdings, index constituents, fundamentals, news, AI analysis, or saved
  chart layouts.
- Replacing the existing full stock detail workflow.
