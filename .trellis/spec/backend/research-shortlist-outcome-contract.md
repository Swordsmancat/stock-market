# Research Shortlist Outcome Contract

## Scenario: Frozen Outcomes for Published A-share Research Cohorts

### 1. Scope / Trigger

- Trigger: a committed daily research shortlist needs evidence-based 5, 20,
  and 60-session follow-up without changing the published cohort.
- Scope: `ResearchCandidateOutcome`, Alembic revision
  `0021_research_shortlist_outcomes`,
  `packages/services/research_shortlist_outcomes.py`, the outcome FastAPI/Next
  routes, and the independently degradable outcome panel on AI Research.
- Non-goals: portfolio backtesting, transaction costs, position sizing,
  threshold optimization, trading instructions, provider fallback, benchmark
  creation, or automatic changes to later shortlist membership and rank.

### 2. Signatures

- Database identity:
  `research_candidate_outcomes(candidate_id, horizon_sessions)` with one
  terminal row per candidate and allowed horizon `5|20|60`.
- Read service:
  `get_research_shortlist_outcomes(run_id, *, session, as_of=None, now=None,
  verified_completed_through=None)`.
- Write service:
  `evaluate_research_shortlist_outcomes(run_id, *, session, as_of=None,
  now=None, verified_completed_through=None,
  evaluation_task_run_id=None)`.
- Bounded due-batch service:
  `evaluate_due_research_shortlist_outcomes(*, session, market, profile_id,
  verified_completed_through, evaluation_task_run_id, run_limit=25,
  now=None, progress=None)`.
- Tracking service:
  `get_research_shortlist_outcome_tracking(*, session, market="CN",
  profile_id="balanced_research", limit=10, offset=0, as_of=None, now=None)`.
- APIs:
  - `GET /research-shortlists/{run_id}/outcomes?as_of=YYYY-MM-DD`
  - `POST /research-shortlists/{run_id}/outcomes/evaluate` with optional
    `{ "as_of": "YYYY-MM-DD" }`
  - `GET /research-shortlists/tracking?market=CN&profile_id=...&limit=1..50&offset>=0`

### 3. Contracts

- Horizon N matures on the candidate's Nth distinct completed `DailyBar`
  strictly after its frozen entry date. The entry row and incomplete rows do
  not consume a forward position; suspension gaps do not count.
- A bar is completed only when `ingested_at` is at or after 16:00
  Asia/Shanghai on its trade date or on a later Shanghai date. SQLite stores
  naive timestamps as UTC and compares against `datetime(trade_date,
  '+8 hours')`; PostgreSQL compares against `timezone('Asia/Shanghai',
  CAST(trade_date AS timestamp) + INTERVAL '16 hours')` so session timezone
  cannot alter eligibility.
- Public `as_of` defaults to the previous Shanghai calendar date. The internal
  verified watermark is not exposed through FastAPI. `as_of` limits market
  observation dates, not when a later finalized backfill became known.
- GET never writes. Missing terminal rows are derived as `pending`, cap progress
  at `N/N`, expose `ready_for_evaluation=true` at N, and keep all metrics null.
- POST freezes either `evaluated` or structured `blocked` candidate fields.
  Repeated calls, concurrent calls, and later `DailyBar` replacement do not
  revise candidate terminal values. A pending benchmark may transition once.
- Terminal payloads expose the nullable `evaluation_task_run_id` that created
  the candidate observation. Derived pending horizons expose null. Later
  benchmark repair preserves the original candidate evaluation lineage.
- Evaluation reads only local `DailyBar` rows. It must not call providers,
  payload fallback services, or network clients.
- Adjustment bases are `qfq`, `hfq`, and `raw`; unknown or mixed bases block.
  `tushare.pro.daily` is effectively raw even for legacy rows mislabeled qfq.
- The only benchmark identity is `CN/index/cn_csi_300`. Candidate entry and
  maturity dates require exact benchmark-date matches; stock `000300` is not a
  substitute. Missing benchmark evidence leaves absolute candidate metrics
  valid and relative metrics null.
- Candidate bar loading is keyed by `ResearchShortlistCandidate.id`, not
  instrument ID. A candidate-scope CTE uses a conditional cumulative window
  and filters `forward_position <= 60` outside the window subquery. It rejoins
  `DailyBar` by `(instrument_id, trade_date)`, yielding at most entry plus 60
  ORM rows per candidate. Incomplete-forward presence is grouped once per
  candidate and outer-joined, never projected as a repeated correlated scan.
- Tracking loads latest plus paginated earlier cohorts in bulk. SELECT count is
  constant across limits 1, 10, and 50 and remains within the tested budget.
- Every payload preserves `research_signal_only=true`, nullable missing
  metrics, structured diagnostic codes, and no buy/sell/hold, target, sizing,
  order, broker, or execution intent.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Run missing or not committed | Detail/evaluate returns not found; no writes |
| Future or untrusted current-date `as_of` | Reject before loading observations |
| Fewer than N completed forward bars | Derived pending `min(count, N)/N`; no row |
| N bars exist but POST has not run | Pending `N/N`, ready true, metrics null |
| Entry missing, incomplete, revised, or unknown basis | Terminal blocked code; metrics null |
| Forward price/OHLC/basis invalid | Terminal blocked code; metrics null |
| Entry bar missing with 61+ forward bars | Load only first 60 forward rows; block at 60 |
| Incomplete forward bars exist | Ignore them for positions and emit structured diagnostic |
| Canonical benchmark or exact date missing | Candidate result remains evaluated; relative fields null |
| Same instrument appears in multiple cohorts | Independent candidate-ID windows from each entry date |
| Due batch limit is outside `1..100` | `ValueError`; no cohort evaluation |
| Later terminal maturity is after historical `as_of` | Hide terminal row and derive earlier pending progress |
| Tracking has no committed cohort | HTTP 200 `status="no_data"` with safety and pagination shape |

### 5. Good / Base / Bad Cases

- Good: entry plus 60 completed forward rows materialize immutable 5D, 20D,
  and 60D observations with exact maturity dates and frozen provenance.
- Good: two cohorts share one instrument but each window starts at its own
  candidate entry and returns at most entry plus 60 completed rows.
- Base: 59 completed rows plus any number of incomplete rows remains pending
  `59/60` and exposes `INCOMPLETE_FORWARD_BAR_IGNORED`.
- Base: the canonical benchmark is absent; candidate return and drawdown remain
  valid while benchmark and excess return stay null.
- Bad: loading every instrument bar from the earliest history date through
  `as_of`, grouping by instrument ID, or slicing after materialization.
- Bad: treating a read-time calculation as terminal, matching benchmark arrays
  by position, or feeding outcomes back into shortlist scoring automatically.

### 6. Tests Required

- Boundaries: 4/5, 19/20, 59/60, entry exclusion, N+1 exclusion,
  suspensions, rising-path zero drawdown, and intermediate minimum low.
- Completion: 07:59:59 UTC excluded, 08:00 UTC accepted, later-date backfill
  accepted, naive SQLite timestamps interpreted as UTC, and current-day
  verified watermark gated after Shanghai close.
- Window query: more than 400 stored rows return exactly entry plus 60; missing
  entry returns only 60; no bar still returns an empty candidate window; two
  candidates sharing an instrument retain independent entry/maturity dates.
- Persistence: evaluated/blocked constraints, unique horizon identity,
  conflict-ignore concurrency, immutable terminal values, and one-way
  benchmark completion with original evaluation TaskRun lineage.
- Due batching: literal 5/20/60 probes, oldest-first candidate priority,
  exact-date benchmark repair, inactive candidates, sentinel `has_more`,
  `1..100` validation, isolated failures, and concurrent reuse.
- Benchmark: canonical index identity, stock `000300` rejection, exact dates,
  missing/invalid basis, and nullable sample semantics.
- API/UI: GET remains non-mutating, POST idempotent, tracking pagination/no-data,
  localized structured diagnostics, cohort synchronization, mobile table
  scrolling, and isolated panel errors.
- Final gate: full pytest, full Vitest, TypeScript, Ruff, locale JSON, Alembic
  head/current, Trellis validation, PostgreSQL migration, and desktop/mobile
  browser QA.

### 7. Wrong vs Correct

#### Wrong

```python
rows = session.query(DailyBar).filter(
    DailyBar.instrument_id.in_(instrument_ids),
    DailyBar.trade_date >= earliest_entry_date,
    DailyBar.trade_date <= as_of,
).all()
bars_by_instrument = group_by_instrument(rows)
```

This materializes years of irrelevant history and cannot isolate two cohorts
that share an instrument but have different entry dates.

#### Correct

```python
scope = candidate_scope(candidate_ids)
ranked = completed_candidate_rows_with_forward_position(scope, as_of)
keys = ranked.where(ranked.c.forward_position <= 60)
rows = join_daily_bars_by_composite_key(scope, keys)
bars_by_candidate = group_by_candidate_id(rows)
```

The database returns only the entry row plus the first 60 completed forward
observations for each immutable candidate, while preserving an empty window and
candidate-level incomplete diagnostic when evidence is missing.
