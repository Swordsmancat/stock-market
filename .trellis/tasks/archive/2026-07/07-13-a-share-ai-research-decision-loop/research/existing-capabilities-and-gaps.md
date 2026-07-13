# Existing capabilities and gaps

## Scope

Read-only audit of the current stock-selection, historical-evaluation, data
persistence, worker, and AI Research UI paths. The code knowledge graph did not
contain this repository and its indexing worker failed twice, so discovery fell
back to focused source/test/spec inspection as permitted by `AGENTS.md`.

## Reusable selection and explanation path

- `packages/services/stock_selection.py`: full active-instrument scan, bulk
  daily-bar/technical/fundamental/news evidence loading, criteria diagnostics,
  coverage, and evidence IDs.
- `packages/services/stock_selection_profiles.py`: three visible profiles and
  validated overrides.
- `packages/services/stock_discovery.py`: bounded shortlist and fail-closed AI
  explanation.
- `packages/ai/stock_discovery.py`: prompt and unknown-symbol/citation checks.
- `apps/api/routers/stock_selection.py`: profile, coverage, universe, discover,
  and screen APIs.
- `tests/services/test_stock_selection.py`,
  `tests/services/test_stock_discovery.py`, and
  `tests/api/test_stock_selection_api.py`: current compatibility coverage.

## Critical ranking defect

The selector rejects a candidate when any active criterion fails. For returned
candidates, score is matched criteria divided by active criteria, so every
eligible candidate normally scores `1.0`. Sorting then falls through to symbol
descending. Existing tests encode this behavior. The first snapshot must define
a separate meaningful score before persisting rank.

## Evidence boundaries

- Candidate payloads already include latest bar, fundamentals, technical
  indicators, matched rules, and evidence IDs.
- `packages/services/market_assistant.py` and related evidence builders already
  expose richer official-disclosure, disclosure-section, market-daily, report,
  news, and notebook citations.
- Current selection uses latest evidence without a point-in-time cutoff. It is
  valid for a new current-day snapshot but unsafe for historical reconstruction.
- Current news article count is historical rather than freshness-windowed.

## Persistence and operations

- No shortlist run, candidate, tracking, or outcome table exists.
- The web panel stores discovery output only in React state.
- `ResearchBrief`, `GeneratedReport`, watchlist, portfolio, and
  `TaskRun.result_json` have different semantics and must not be repurposed.
- `TaskRun`, report-worker, and Celery Beat patterns can provide lineage and
  scheduling after domain persistence exists.

## Outcome audit

- `smart_recommendations.py` and `strategy_screening.py` provide deterministic
  forward return, hit-rate, drawdown, distribution, and benchmark formula ideas.
- Both are stateless research evaluators, not candidate ledgers.
- Their benchmark calculation aligns arrays by position, not exact trading date.
- `get_bars_payload` may return a partial DB range or call a provider; a formal
  outcome worker must query local `DailyBar` rows directly.
- `DailyBar` rows may be replaced by source-priority ingestion. Entry/exit values
  and provenance must therefore be frozen when published.
- Portfolio fallbacks may substitute average cost for a missing latest price and
  must never be used for shortlist outcome calculation.

## Required outcome invariants

- Start with post-deployment snapshots; no historical shortlist fabrication.
- Entry is the frozen decision-date close observation.
- Horizon N is the Nth distinct stored bar after entry.
- Fewer than N bars remains pending; invalid/missing evidence remains null with
  diagnostics.
- Candidate and CSI 300 benchmark bars align by exact entry/exit dates.
- Adjustment mismatch blocks calculation.
- Aggregates retain inactive/delisted members and expose every denominator.

## UI audit

- Keep the existing `/ai-research` route and navigation entry.
- Put the persisted daily shortlist first; move evidence coverage and manual
  discovery into secondary data-preparation positions.
- Reuse `/instruments/{symbol}` for deep analysis and the existing browser event
  for optional in-page symbol handoff.
- Do not use watchlists as outcome tracking and do not make the legacy
  technical-only `SmartRecommendations` component the new primary shortlist.
- Latest-snapshot failure must degrade independently so the existing research
  desk remains usable.
