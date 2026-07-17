# Add stored market movers ranking

## Goal

Add a fast, trustworthy A-share gainers/losers page for personal market review,
using only the latest coherent daily bars already stored in PostgreSQL.

## Requirements

- Add a read-only `GET /market-movers` endpoint for `CN` active stocks.
- Support `direction=gainers|losers`, exchange `all|SSE|SZSE|BSE`, and bounded
  result limits `10|20|50`.
- Select the newest stored trade date that has an earlier stored trade date.
  Compare exact closes on those two market dates; never substitute a stale
  per-symbol close from a different date.
- Choose one deterministic dominant `provider + adjustment` cohort for the
  selected date and require each comparison row to use that same cohort on
  both dates. Do not mix incompatible provenance to inflate coverage.
- Exclude rows with missing, zero, negative, or non-finite previous closes and
  rows whose latest/previous bars do not share the selected cohort.
- Rank by percentage change, then absolute change, then symbol for stable
  ordering. Gainers sort descending; losers sort ascending.
- Return trade dates, cohort provenance, source distribution, eligible count,
  omitted count, and exact symbol/name/exchange/close/change/volume/amount
  fields. Numeric values must serialize safely.
- Return explicit `no_data` when no coherent two-date cohort exists; do not
  fall back to fixtures, provider calls, or fabricated values.
- Add `/[locale]/market-movers` as a compact table-oriented page with a
  gainers/losers segmented control, exchange filter, and 10/20/50 row control.
- Each row must link to the exact CN instrument detail route.
- Add a desktop sidebar entry without changing the existing mobile set.
- Localize all visible Chinese and English text and provide accessible table,
  filter, empty, degraded, and load-failure states.

## Acceptance Criteria

- [ ] Service tests prove latest/previous date selection, dominant cohort
      selection, exact-date comparison, exchange filters, stable ordering,
      invalid previous-close omission, and no-data behavior.
- [ ] API tests prove query validation and database-session delegation.
- [ ] The page renders stored dates/provenance, gainers and losers, filters,
      exact detail links, empty/load-failure states, and responsive tables.
- [ ] Page rendering and the API perform no provider request or mutation.
- [ ] Navigation and breadcrumb labels are available in both locales, with the
      mobile navigation unchanged.
- [ ] Focused backend/frontend tests, Ruff, TypeScript, locale JSON parsing,
      Trellis validation, and `git diff --check` pass.

## Out of Scope

- Intraday/live movers, streaming quotes, limit-up pools, fund-flow ranking,
  AI stock selection, historical ranking storage, or automated refresh.
- ETFs, indexes, funds, futures, Hong Kong/US markets, or custom date ranges.
- New ingestion schedules or changes to the existing 95/90/80 research gates.
