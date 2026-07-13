# A-share AI research decision loop - design

## Architecture

Implement the loop as three independently testable child tasks over existing
domain boundaries:

1. shortlist generation and immutable snapshot publication;
2. candidate outcome ledger and cohort metrics;
3. daily orchestration and operational acceptance.

The parent task has no direct code implementation. It owns the shared contracts
below and the final cross-child review.

## Existing boundaries to reuse

- `stock_selection.py` remains the local eligibility engine and bulk evidence
  loader.
- `stock_discovery.py` remains the fail-closed AI explanation boundary. AI never
  controls candidate membership or rank.
- `MarketAssistantCitation` and existing evidence builders remain the source of
  rich, source-transparent citation metadata.
- `DailyBar` is the only V1 price observation ledger.
- `TaskRun` records operational lineage but does not store queryable shortlist
  or outcome domain state.
- `/ai-research` remains the top-level workflow; `/instruments/{symbol}` remains
  the deep-analysis destination.

## Domain model

### ResearchShortlistRun

An immutable published decision snapshot with:

- decision date, generation timestamp, market, profile, and scope;
- rule-set and scoring-model versions;
- criteria/weight snapshots and deterministic generation key;
- universe and evidence coverage, diagnostics, citations, model, and safety;
- optional TaskRun lineage.

### ResearchShortlistCandidate

An immutable ranked member of one run with:

- instrument identity plus symbol/name/market snapshots;
- rank, total score, and factor-score JSON;
- supporting/opposing factors, data gaps, invalidation conditions, and citation
  snapshots;
- entry trade date/close plus bar provider/source/adjustment/priority/ingestion
  provenance.

The run owns unique rank and instrument constraints. A candidate must use a bar
whose trade date equals the run decision date; stale candidates are excluded or
explicitly rejected before publication.

### ResearchCandidateOutcome

One immutable terminal observation per candidate and horizon (`5`, `20`, `60`)
with:

- evaluated/blocked status, available forward-bar count, and maturity cutoff;
- exit date/close, return, future drawdown, and frozen price provenance;
- independently progressing exact-date benchmark status/data, return, and
  excess return;
- diagnostics and evaluation timestamp.

Before terminal materialization, pending is a read-model state derived from the
frozen candidate and local forward bars. With fewer than N eligible bars it is
not data-ready; with at least N bars it reports `N/N` and
`ready_for_evaluation=true` until an explicit evaluator freezes evaluated or
blocked. Public responses still expose all three horizons for every candidate.
This refinement avoids mutating progress rows while preserving the parent
requirement for visible pending/evaluated/blocked counts.

This table is introduced by the outcome child, not pre-created speculatively by
the snapshot child.

## Scoring contract

Eligibility and ranking are separate:

1. Existing visible profile criteria decide eligibility and continue to fail
   closed on missing required evidence.
2. A versioned scorer maps the eligible candidate's frozen fundamental,
   technical, liquidity, and optional news facts to bounded factor scores.
3. Each factor exposes its inputs, normalization, contribution, and weight.
4. The weighted total determines order. Stable ties use symbol ascending only
   after the score and evidence-coverage tie-breakers.
5. Numeric weights sum to one over configured factors. Missing optional factors
   do not silently improve the score; their missing policy and penalty are
   explicit.

Scoring must not assign numeric influence to prose, LLM output, official
disclosures, or market events until a deterministic mapping has its own review.
Those sources may enrich supporting/opposing context and citations.

## Snapshot generation flow

1. Resolve profile and visible overrides.
2. Determine a completed A-share decision date/watermark.
3. Bulk-load local evidence at that watermark and apply eligibility gates.
4. Score eligible candidates and build structured reasons/gaps/invalidation.
5. Generate an optional explanation from the fixed ranked candidates and
   allowed citations; fail closed to deterministic text.
6. Persist run and candidate rows in one transaction using the generation key.
7. Return the already-persisted snapshot for duplicate requests.

No live provider fetch occurs inside publication.

## Outcome semantics

- Entry is a frozen closing-price observation, not an assumed fill.
- Horizon N is the Nth distinct local `DailyBar` after entry.
- Return is `exit_close / entry_close - 1`.
- Drawdown uses the minimum low over forward bars 1..N relative to entry close.
- Candidate and benchmark bars join by exact trade date. V1 benchmark is the
  dedicated local CSI 300 instrument identified by
  `market=CN`, `asset_type=index`, `symbol=cn_csi_300`; stock `000300` is never
  a benchmark substitute.
- Different adjustment modes block evaluation with a diagnostic.
- Fewer than N eligible completed bars remains pending and not ready. Once N
  exist but before evaluation, the read model remains pending `N/N` and ready;
  evaluation then freezes invalid candidate entry/path values or incompatible
  adjustment as blocked/null.
  Missing benchmark bars leave the candidate evaluated while benchmark and
  relative fields remain pending/null. No missing state becomes a zero return.
- Published candidate terminal outcomes are immutable; an explicit future
  revision mechanism is required to recalculate after source replacement. A
  missing benchmark may make one independent transition from pending to a
  frozen evaluated/blocked benchmark observation on the same terminal row.

The outcome worker queries `DailyBar` directly. It must not call
`get_bars_payload` or any provider fallback.

## API shape

Snapshot child:

- `POST /research-shortlists/generate`
- `GET /research-shortlists/latest`
- `GET /research-shortlists/{run_id}`

Outcome child adds tracking/history and outcome retrieval under the same
resource family. Responses include status, as-of lineage, structured candidates,
coverage/diagnostics, citations, safety, and `research_signal_only=true`.

## Frontend flow

- Load latest snapshot server-side as an optional dependency of `/ai-research`.
- Render a new daily-shortlist panel first with a dense comparison table.
- Keep data coverage and manual discovery below it as secondary tooling.
- Link candidates to `/instruments/{symbol}` and preserve the existing in-page
  symbol handoff for quick expansion.
- A failed or absent latest snapshot must not make the rest of AI Research
  unavailable.

## Compatibility and rollout

- Keep existing `/stock-selection/screen` and `/discover` contracts compatible.
- Add schema and APIs incrementally; do not repurpose existing brief/report,
  watchlist, portfolio, or TaskRun storage.
- Manual generation is the first acceptance path. Scheduling is enabled only
  after snapshot and outcome services are independently green.
- Rollback removes the new panel/routes and downgrades only the new tables; old
  research workflows remain available.

## Main risks

- Persisting the current `1.0` score would create a false baseline; the snapshot
  child must fix ranking before publication.
- Reconstructing old cohorts with latest evidence creates look-ahead bias; V1
  begins from deployment.
- Array-position benchmark alignment creates false relative returns; exact-date
  joins are mandatory.
- Source replacement can change historical bars; every published observation
  freezes values and provenance.
