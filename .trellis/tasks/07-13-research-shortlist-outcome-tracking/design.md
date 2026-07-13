# Research shortlist outcome tracking - design

## Product boundary

The feature is a feedback surface for published research cohorts. It measures
candidate observations; it does not simulate a portfolio or feed results back
into selection. The existing immutable shortlist remains the source of cohort
membership and entry evidence.

## Architecture

Add one terminal outcome ledger and a separate read/evaluation service:

1. `ResearchShortlistCandidate` supplies immutable cohort identity and entry.
2. `DailyBar` supplies local candidate and benchmark observations up to a
   completed-day cutoff.
3. `ResearchCandidateOutcome` freezes a mature candidate result and an
   independently progressing benchmark observation.
4. A service materializes all three public horizon states, aggregates cohorts,
   and powers manual API and future worker callers.
5. A dedicated frontend outcome module loads independently of the existing
   daily-shortlist contract.

No provider adapters or payload services are on this path.

## Persistence model

Create `research_candidate_outcomes` in Alembic revision `0021` with:

- identity: `id`, `candidate_id`, `horizon_sessions`, unique
  `(candidate_id, horizon_sessions)`;
- methodology: `methodology_version=research_candidate_outcome_v1`, terminal
  `status` constrained to `evaluated|blocked`, `evaluation_as_of`,
  `available_forward_bars`, optional TaskRun lineage;
- frozen candidate result: required maturity date, exit close, minimum low and its date,
  `return_ratio`, `drawdown_ratio`, and exit/low provider, source, adjustment,
  source-priority, and ingestion timestamps;
- benchmark identity/state: `benchmark_code=cn_csi_300`, nullable canonical
  instrument ID, `benchmark_status` constrained to
  `pending|evaluated|blocked|not_applicable`;
- frozen benchmark entry/exit dates, closes, provenance,
  `benchmark_return_ratio`, and `excess_return_ratio`;
- structured diagnostics plus created/evaluated/benchmark-completed timestamps.

Candidate deletion cascades to outcomes. Outcome numeric fields use decimal
ratios, not the legacy evaluator's percentage-point representation. The model
does not store pending candidate rows: absence plus current bulk bar counts is
the pending state. This removes a mutable progress row while still presenting
three fixed horizon records per candidate in every API response.

Candidate terminal fields never change. While a benchmark remains pending, its
canonical instrument ID and structured missing-evidence diagnostics may refresh
conditionally, but all benchmark observations and ratios remain null. The only
metric enrichment is a one-way benchmark transition from `pending` to
`evaluated` or `blocked` using the already-frozen entry and maturity dates.
There is no update/delete/revision API.

## Completed-day cutoff

The service accepts `as_of` and an injectable clock. Its manual/API upper bound
is always the previous Asia/Shanghai calendar date. This deliberate one-day
lag prevents a close-time wall clock from blessing an intraday row that was
written before market close and never refreshed. Weekends and holidays need no
special calendar substitution because only stored bars count.

- Explicit `as_of` later than that upper bound is rejected.
- Manual calls default to the upper bound and reject the current local date even
  after market close.
- The service has an internal-only optional `verified_completed_through`
  parameter for the automation child. When supplied, the allowed upper bound is
  the trusted watermark capped at the current Shanghai date; using the current
  date also requires local time at or after 16:00. Browser/FastAPI request
  models never expose this parameter, and it never bypasses per-bar ingestion
  completion checks.
- Every candidate and benchmark query includes `trade_date <= as_of`.
- After the date filter, a bar is eligible only if `ingested_at`, converted to
  Asia/Shanghai, is at or after 16:00 on its own trade date or falls on a later
  local date. Naive SQLite timestamps are normalized as UTC, matching the model
  write default. Earlier same-day rows are ignored and surfaced as structured
  incomplete-evidence diagnostics; they do not count toward N.

`as_of` is a market observation-date cutoff, not a bitemporal system-time
snapshot. A finalized bar ingested later may be used when its `trade_date` is no
later than `as_of`; `ingested_at` proves own-day completion but is not an
additional known-by cutoff. The immutable shortlist entry remains the
point-in-time decision record.
- Reads expose a stored terminal row only when its frozen maturity date is
  `<= as_of`. For an earlier historical cutoff the serializer ignores that row
  and derives pending/progress from candidate bars through the cutoff. The
  evaluation timestamp is audit lineage, not the horizon's effective date.

## Read and evaluation algorithms

Both paths bulk-load candidates, existing terminal outcomes, canonical entry
bars, and enough post-entry bars to obtain the first 60 completed observations
after the ingestion-time rule. Query count remains constant with candidate
count.

GET/read path:

1. Never acquires a write lock or writes an outcome.
2. Reuse a visible terminal row whose maturity date is within `as_of`.
3. For every absent/hidden horizon, emit derived pending progress as
   `min(actual_forward_bars, N)`. Set `ready_for_evaluation=true` at N; all
   metrics remain null.
4. Serialize aggregates and diagnostics.

POST/worker evaluation path for one committed run:

1. Acquire a run-scoped PostgreSQL transaction advisory lock; SQLite/test
   runtimes use the existing bounded process-local lock pattern.
2. Reuse every already-terminal candidate observation; only a pending benchmark
   may progress.
3. For an absent horizon with fewer than N completed bars, return derived
   pending and write nothing.
4. At N bars, validate positive finite OHLC values, internal OHLC consistency,
   known and consistent adjustment, and equality of the current entry close and
   adjustment to the frozen candidate entry. The frozen and current entry
   provenance must also satisfy the completed-bar ingestion rule.
   Provider/source changes alone are allowed.
5. On validation failure, stage one terminal blocked row with a structured code
   and null result metrics. Otherwise stage an evaluated row with the Nth close,
   minimum low over bars 1..N, provenance, return ratio, and drawdown ratio.
6. Bulk-resolve only the canonical `CN/index/cn_csi_300` instrument. For each
   evaluated candidate, exact-join benchmark bars on frozen entry and maturity
   dates. Missing identity or either date leaves benchmark pending and relative
   fields null. Invalid/mismatched benchmark basis is benchmark-blocked. Valid
   exact bars freeze benchmark and excess ratios.
7. Conflict-ignore insert staged terminal rows, conditionally enrich pending
   benchmarks, commit once, reload, and serialize. Repeated calls reuse
   candidate terminal values.

The database unique constraint is the final concurrency defense. Terminal rows
are inserted with dialect-appropriate `ON CONFLICT DO NOTHING` semantics (or
per-row savepoints on an unsupported dialect), then the complete requested set
is reloaded. A conflict on one 5D row cannot roll back non-conflicting 20D/60D
rows in the same batch. Benchmark enrichment uses a conditional update whose
predicate still requires `benchmark_status=pending`; losers reload the winner.
PostgreSQL row/advisory locks reduce contention, but correctness does not depend
on a process-local lock.

Blocked candidate outcomes are created only when N forward candidate bars are
available; before maturity, the public state remains pending. This avoids
freezing a provisional data defect before the observation horizon exists.

## Adjustment and revision policy

Adjustment normalization has one owner in the outcome service:

- canonical known bases: `qfq`, `hfq`, and `raw`;
- explicit aliases `none`, `unadjusted`, and `no_adjust` normalize to `raw`;
- blank, `unknown`, `legacy_unknown`, and `provider_default` normalize to
  unknown and fail closed;
- `source=tushare.pro.daily` normalizes to `raw` even when a legacy stored row
  says `qfq`, and emits `PROVENANCE_ADJUSTMENT_CORRECTED`.

The ingestion coordinator must label future `tushare.pro.daily` bars as `raw`.
That provider calls `pro.daily` without `adj_factor` or `pro_bar`; it does not
produce qfq prices. A path combining those effective raw bars with AkShare qfq
bars is mixed and blocks. Tests cover corrected coordinator metadata and
legacy-row normalization.

A known qfq/hfq path is accepted as a documented proxy only if the current
canonical entry close and effective adjustment still exactly match the frozen
entry after source-aware normalization. This detects the common historical
rewrite caused by a newer factor vintage, but V1 does not claim factor-vintage
reproducibility.

Once stored, candidate result values and provenance are not recalculated after
bar replacement. Correcting a terminal blocked/evaluated observation requires a
future explicit versioned revision mechanism.

## Benchmark identity

The resolver requires all of:

```text
Market.code = CN
Instrument.asset_type = index
Instrument.symbol = cn_csi_300
```

It never falls back to stock `000300`, an arbitrary index, or provider symbol
mapping. The current provider mapping remains ingestion metadata only. Outcome
evaluation does not create the canonical instrument. CSI 300 is treated as a
price-index research comparator; total-return-index support is out of scope.

Stock and benchmark adjustment strings do not have to equal each other. Each
series must be internally known and consistent across its own entry/exit bars.

## Read model and aggregates

Public candidate records always contain horizon 5, 20, and 60 objects:

- pending: derived count, null exit/metrics;
- pending with N available bars: count capped at N plus
  `ready_for_evaluation=true`, still null exit/metrics until POST/worker commit;
- evaluated: frozen candidate metrics plus independent benchmark status;
- blocked: structured diagnostics and null candidate metrics.

Per-horizon aggregates include total/evaluated/pending/blocked, return sample
size, benchmark sample size, positive-return ratio, mean and median return,
mean drawdown, and mean excess return. Inactive instruments are never filtered.
All calculations ignore nulls and return null for an empty sample.

Tracking loads the complete requested page of runs, candidates, outcomes, and
bar-count projections in bulk. Its query count is bounded for `limit=1`, 10, or
50 and must not grow per cohort or candidate.

## API contracts

Add routes before the existing dynamic `/{run_id}` route where required:

- `POST /research-shortlists/{run_id}/outcomes/evaluate`
  - body: optional `as_of` only;
  - 200 for domain states including blocked/pending;
  - 400 for invalid/future cutoff, 404 for missing run.
- `GET /research-shortlists/{run_id}/outcomes?as_of=<date>`
  - complete candidate/horizon detail without mutating state.
- `GET /research-shortlists/tracking?market=CN&profile_id=balanced_research&limit=10&offset=0&as_of=<date>`
  - latest cohort detail plus paginated recent cohort aggregates;
  - `limit` defaults to 10 and is constrained to `1..50`; `offset >= 0`;
  - remains scoped to committed shortlist cohorts for one market/profile and
    does not expose configurable strategy/backtest dimensions;
  - 200 `no_data` when no committed run exists.

Responses retain `research_signal_only=true` and the existing safety shape.
Existing generate/latest/detail response schemas do not change.

Service entry points accept optional `evaluation_task_run_id` for the later
automation child, but the browser API does not accept caller-supplied lineage.

## Frontend design

Add `ResearchShortlistOutcomePanel` after `DailyResearchShortlistPanel` and
before `AiResearchDesk`. It owns its own payload, loading/update error, and
refresh state.

- Summary: dense 5D/20D/60D rows with status counts and nullable metrics.
- Candidate matrix: symbol/rank plus three stable-width horizon cells.
- History: compact recent cohort table with decision date and samples.
- Update control: icon plus localized label, disabled while evaluating.
- Cohort synchronization: the server page keys/remounts the client panel by the
  tracking run ID (or explicitly replaces state when that ID changes), so the
  existing shortlist `router.refresh()` cannot leave old outcome state beside
  a newly generated shortlist.
- Mobile: horizontal table regions or stacked candidate rows with stable tracks;
  no content overlap or page-level horizontal overflow.
- Diagnostics: map known structured codes to both locale catalogs; unknown codes
  use a localized generic format and never render backend prose.

Add no-store Next proxies for tracking, outcome detail, and evaluation. A failed
tracking request renders only the outcome panel error state.

## Diagnostics

Initial structured codes include:

- `ENTRY_BAR_MISSING`, `ENTRY_BAR_REVISED`, `ENTRY_ADJUSTMENT_UNKNOWN`;
- `ENTRY_BAR_INCOMPLETE`, `INCOMPLETE_FORWARD_BAR_IGNORED`;
- `FORWARD_PRICE_INVALID`, `FORWARD_OHLC_INVALID`,
  `FORWARD_ADJUSTMENT_UNKNOWN`, `FORWARD_ADJUSTMENT_MISMATCH`;
- `INSTRUMENT_INACTIVE` as a non-blocking diagnostic;
- `BENCHMARK_INSTRUMENT_MISSING`, `BENCHMARK_ENTRY_MISSING`,
  `BENCHMARK_EXIT_MISSING`, `BENCHMARK_PRICE_INVALID`,
  `BENCHMARK_ADJUSTMENT_UNKNOWN`, `BENCHMARK_ADJUSTMENT_MISMATCH`;
- `QFQ_PROXY_BASIS` as an explicit methodology diagnostic.
- `PROVENANCE_ADJUSTMENT_CORRECTED` for the known legacy Tushare raw/qfq label.

## Compatibility, rollout, and rollback

- Revision `0021` adds one table; no existing rows or APIs are rewritten.
- Backend can ship before UI because the existing shortlist path is untouched.
- Scheduling remains disabled until the next child task.
- Rollback removes the new panel/proxies/routes and downgrades only `0021`;
  shortlist runs/candidates remain intact.

## Main risks

- qfq values can change without a stored factor vintage. The frozen-entry
  equality guard reduces, but does not eliminate, this risk.
- Existing Tushare daily rows may carry the historical wrong `qfq` label. The
  source-aware raw normalization is mandatory; comparing stored strings alone
  would freeze false mixed-provider returns.
- A benchmark may remain unavailable until a dedicated canonical index loader
  exists. This is honest null evidence, not a reason to block absolute results.
- History reads could drift into N+1 queries. Bulk candidates/outcomes/bar
  counts and query-count tests are required.
- Client state can drift across a server refresh. A sibling/page integration
  test must prove both panels advance to the same run ID after generation.
