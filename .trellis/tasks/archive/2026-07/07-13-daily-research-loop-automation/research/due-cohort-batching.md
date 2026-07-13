# Due-cohort selection and bounded outcome batching

## Scope

This note designs the read-side selector and bounded batch semantics for the
daily research loop. It does not change runtime code. The selector must find
historical shortlist runs for which the existing outcome evaluator can make a
durable state transition, while preserving the outcome ledger's local-data,
completed-day, immutable, and research-only contracts.

The recommended design is a self-draining database work set, not a durable
queue and not an offset cursor.

## Executive recommendation

Add two service-level operations in
`packages/services/research_shortlist_outcomes.py`:

```python
@dataclass(frozen=True)
class DueResearchShortlistRun:
    run_id: UUID
    due_since: date
    reasons: frozenset[Literal["candidate_terminal", "benchmark_repair"]]


def select_due_research_shortlist_runs(
    *,
    session: Session,
    market: str,
    profile_id: str,
    completed_through: date,
    run_limit: int = 25,
) -> list[DueResearchShortlistRun]: ...


def evaluate_due_research_shortlist_outcomes(
    *,
    session: Session,
    market: str,
    profile_id: str,
    completed_through: date,
    evaluation_task_run_id: UUID,
    run_limit: int = 25,
) -> dict[str, object]: ...
```

Use a configurable default such as 25 and a hard maximum of 100. One run has
at most 20 published candidates through the current API, and the existing bar
window returns at most entry plus 60 rows per candidate. The hard maximum is a
work bound, not a pagination promise.

Selection has two lanes:

1. **Candidate-terminal lane, first:** a `(candidate, horizon)` has no terminal
   row and its Nth completed forward bar now exists through the trusted cutoff.
2. **Benchmark-repair lane, remaining slots only:** an evaluated outcome still
   has `benchmark_status=pending`, and the current canonical CSI 300 instrument
   now has completion-eligible bars on the exact candidate entry and maturity
   dates.

Do not select genuinely immature horizons with fewer than N completed bars.
In this note, "candidate not terminal" means absence of the immutable outcome
row; only a horizon-ready absence is due. Public `pending` alone is not a due
predicate because it includes both `4/5` and ready-but-uncommitted `5/5`.

Do not select benchmark-pending rows merely because their status is pending.
Missing canonical identity or missing exact-date evidence is an honest waiting
state, not daily work. This is what prevents a permanently missing benchmark
from occupying every bounded batch.

## Existing guarantees to reuse

The selector should only decide *which run IDs to call*. It must not duplicate
evaluation behavior.

- `evaluate_research_shortlist_outcomes()` resolves the trusted cutoff, takes
  the run-scoped lock, reloads the committed run/candidates/bars/outcomes, then
  commits one serialized result
  (`packages/services/research_shortlist_outcomes.py:91-167`).
- Candidate windows are keyed by immutable candidate ID and use a conditional
  cumulative position, returning at most entry plus the first 60 completed
  forward rows (`packages/services/research_shortlist_outcomes.py:336-464`).
- Staging skips an existing `(candidate, horizon)` and does nothing below the
  strict horizon boundary (`packages/services/research_shortlist_outcomes.py:528-590`).
- Candidate terminal inserts use `ON CONFLICT DO NOTHING` for PostgreSQL and
  SQLite (`packages/services/research_shortlist_outcomes.py:868-887`).
- Benchmark enrichment updates only while the stored status is still pending
  (`packages/services/research_shortlist_outcomes.py:899-939`).
- PostgreSQL uses a transaction advisory lock per shortlist run; SQLite/test
  runtimes use bounded striped locks, with the database unique constraint as
  the final defense (`packages/services/research_shortlist_outcomes.py:942-977`).
- The model permits only terminal candidate statuses, has unique
  `(candidate_id, horizon_sessions)`, and constrains benchmark state to a
  one-way-compatible shape (`packages/domain/models.py:859-994`).
- `evaluation_task_run_id` already records the TaskRun that first inserts a
  candidate terminal observation (`packages/domain/models.py:996-1013`).

The tests already prove concurrent one-row convergence, overlapping-horizon
conflict recovery, immutable candidate values, and one-way benchmark behavior
(`tests/services/test_research_shortlist_outcomes.py:336-475,608-643,681-770`).
The automation tests should treat those as imported domain guarantees and test
only selector/batch composition around them.

## Exact due predicates

### Candidate terminal due

For each literal horizon `h` in `(5, 20, 60)`, a candidate is due when all are
true:

- its run is committed and matches `market=CN`, `asset_type=stock`, and the
  configured profile;
- no `ResearchCandidateOutcome` exists for `(candidate.id, h)`;
- the h-th distinct `DailyBar` strictly after `entry_trade_date`, on or before
  `completed_through`, and satisfying the shared completion predicate exists.

The selector must not require the entry bar. Five completed forward bars make
a missing-entry candidate due so the evaluator can freeze
`ENTRY_BAR_MISSING`; otherwise that defect would remain pending forever. The
existing missing-entry regression expects 60 forward rows to produce a blocked
60D terminal observation
(`tests/services/test_research_shortlist_outcomes.py:959-987`).

Do not filter inactive instruments. They stay in the cohort and may still
evaluate (`tests/services/test_research_shortlist_outcomes.py:646-659`).

Do not prevalidate price, OHLC, source, or adjustment in the selector. Presence
and completed-day eligibility make the horizon actionable; the evaluator owns
validation and may freeze a structured blocked result
(`packages/services/research_shortlist_outcomes.py:593-672`). Duplicating those
rules in the selector would create a second methodology and could leave invalid
evidence pending indefinitely.

### Benchmark repair due

A benchmark repair is due only when all are true:

- the stored candidate outcome is `status=evaluated` and
  `benchmark_status=pending`;
- the parent run matches the committed CN stock/profile scope;
- the canonical instrument resolved by `CN/index/cn_csi_300` currently exists;
- one completion-eligible canonical benchmark bar exists on the candidate's
  exact entry date;
- one completion-eligible canonical benchmark bar exists on the outcome's
  exact maturity date, and that date is not after `completed_through`.

Resolve the current canonical identity exactly as `_canonical_benchmark()`
does (`packages/services/research_shortlist_outcomes.py:497-505`). Do not rely
on the pending row's nullable `benchmark_instrument_id` or stale diagnostic
JSON. This allows a canonical identity introduced later to make the row due.

As with candidates, do **not** prevalidate benchmark prices or adjustment.
Complete exact-date rows with invalid price/basis are due: the evaluator must
transition them once to terminal `benchmark_status=blocked`. The outcome
service deliberately distinguishes missing evidence (`pending`) from invalid
available evidence (`blocked`) at
`packages/services/research_shortlist_outcomes.py:705-787`.

Blocked candidate outcomes are never benchmark due because their benchmark is
`not_applicable`. Evaluated or blocked benchmark observations are already
terminal and must not be selected.

## Query shape

### Candidate query: three literal indexed probes

Generate one query per literal horizon and `UNION ALL` them. A literal offset
keeps the correlated Nth-row probe portable between PostgreSQL and SQLite and
lets the `(instrument_id, trade_date)` primary key stop after at most N eligible
positions.

SQLAlchemy-oriented pseudocode:

```python
def candidate_due_for(horizon: int):
    nth_completed_date = (
        select(DailyBar.trade_date)
        .where(
            DailyBar.instrument_id == ResearchShortlistCandidate.instrument_id,
            DailyBar.trade_date > ResearchShortlistCandidate.entry_trade_date,
            DailyBar.trade_date <= completed_through,
            _completed_bar_predicate(session, DailyBar),
        )
        .order_by(DailyBar.trade_date)
        .offset(horizon - 1)
        .limit(1)
        .correlate(ResearchShortlistCandidate)
        .scalar_subquery()
    )
    terminal_exists = exists().where(
        ResearchCandidateOutcome.candidate_id == ResearchShortlistCandidate.id,
        ResearchCandidateOutcome.horizon_sessions == horizon,
    )
    return select(
        ResearchShortlistCandidate.run_id.label("run_id"),
        nth_completed_date.label("due_since"),
        literal("candidate_terminal").label("reason"),
    ).join(ResearchShortlistRun).where(
        ResearchShortlistRun.status == "committed",
        ResearchShortlistRun.market == market,
        ResearchShortlistRun.asset_type == "stock",
        ResearchShortlistRun.profile_id == profile_id,
        ~terminal_exists,
        nth_completed_date.is_not(None),
    )

candidate_due = union_all(*(candidate_due_for(h) for h in OUTCOME_HORIZONS))
```

Group by run ID after the union and use the earliest Nth-bar date as
`due_since`. The unique outcome key makes `NOT EXISTS` cheap; the bar primary
key is `(instrument_id, trade_date)`
(`packages/domain/models.py:197-215`), and candidate `run_id` is indexed
(`packages/domain/models.py:786-790`).

Do not count every bar to the current date and do not materialize all forward
history merely to decide readiness. The three maximum probes are 5, 20, and 60.

### Benchmark query: exact joins, not a date range

Conceptual SQL:

```sql
WITH canonical_benchmark AS (
  SELECT i.id
  FROM instruments i
  JOIN markets m ON m.id = i.market_id
  WHERE m.code = 'CN'
    AND i.asset_type = 'index'
    AND i.symbol = 'cn_csi_300'
)
SELECT c.run_id,
       MIN(o.maturity_trade_date) AS due_since,
       'benchmark_repair' AS reason
FROM research_candidate_outcomes o
JOIN research_shortlist_candidates c ON c.id = o.candidate_id
JOIN research_shortlist_runs r ON r.id = c.run_id
JOIN canonical_benchmark bi ON TRUE
JOIN bars_1d be
  ON be.instrument_id = bi.id
 AND be.trade_date = c.entry_trade_date
 AND /* shared dialect-aware completed-bar predicate for be */
JOIN bars_1d bx
  ON bx.instrument_id = bi.id
 AND bx.trade_date = o.maturity_trade_date
 AND /* shared dialect-aware completed-bar predicate for bx */
WHERE o.status = 'evaluated'
  AND o.benchmark_status = 'pending'
  AND o.maturity_trade_date <= :completed_through
  AND r.status = 'committed'
  AND r.market = 'CN'
  AND r.asset_type = 'stock'
  AND r.profile_id = :profile_id
GROUP BY c.run_id;
```

Use `_completed_bar_predicate()` for both lanes so selector and evaluator share
the UTC/Shanghai boundary (`packages/services/research_shortlist_outcomes.py:467-479`).

### Deterministic two-lane limiting

1. Query candidate-terminal runs ordered by `due_since ASC`, run
   `decision_date ASC`, then run UUID ASC; take at most `run_limit` unique runs.
2. If slots remain, query actionable benchmark-only runs in the same stable
   order, exclude already selected run IDs, and fill the remaining slots.
3. If one run is due for both reasons, return it once with both reason flags.

Oldest actionable evidence first makes the set self-draining. Avoid `OFFSET`:
after a successful transition, a run no longer matches that predicate, so the
next invocation naturally reaches the next item. A crash loses no cursor and
does not strand unprocessed work.

Candidate-terminal work intentionally has priority over optional benchmark
comparison. A missing benchmark never consumes a slot; an actionable benchmark
repair is finite because the evaluator will make it evaluated or blocked. If a
sustained candidate backlog later requires a benchmark fairness SLA, reserve a
small explicit actionable-benchmark quota. Do not solve fairness by admitting
nonactionable pending rows.

## Bounded evaluation semantics

For each selected run, sequentially call the existing evaluator with:

```python
evaluate_research_shortlist_outcomes(
    run_id,
    session=session,
    as_of=completed_through,
    verified_completed_through=completed_through,
    evaluation_task_run_id=evaluation_task_run_id,
)
```

Process at most `run_limit` unique runs in one orchestration invocation. Each
run owns one transaction through the existing evaluator. Catch a per-run
exception, ensure the session is rolled back, record a bounded structured
failure, and continue. Never hold one outer transaction across the batch.

One selected run may materialize many ready rows in one call. At 60 completed
bars, one call can create 5D, 20D, and 60D rows for every candidate; do not
enqueue three horizon jobs. Similarly, a run due for candidate and benchmark
work is evaluated once.

The current candidate materialization bound is tested as 61 rows per candidate
even when more than 400 bars exist
(`tests/services/test_research_shortlist_outcomes.py:934-1023`). With the API's
20-candidate limit, candidate evidence is bounded by roughly
`run_limit * 20 * 61` ORM bars plus terminal rows.

### Tighten benchmark loading for a true bound

The current `_benchmark_bars()` loads every canonical index row from the
earliest candidate entry through `as_of`
(`packages/services/research_shortlist_outcomes.py:508-525`). A benchmark first
introduced years after an old cohort could therefore make a benchmark-only
repair load years of irrelevant index bars.

Before calling the evaluator path bounded at scale, refactor benchmark loading
to exact required dates:

- every candidate entry date;
- each maturity date for an existing pending benchmark;
- the 5th/20th/60th maturity dates visible in the already-bounded candidate
  windows for newly staged outcomes.

Query `DailyBar.trade_date.in_(required_dates)` for the canonical benchmark.
For one 20-candidate run this is at most 20 entry dates plus 60 maturity dates
before deduplication. This preserves exact-date semantics and makes benchmark
materialization bounded independently of cohort age.

## Idempotency proof

For a fixed trusted cutoff `w`, candidate and benchmark state transitions are
monotone:

```text
candidate: absence -> evaluated | blocked
benchmark: pending -> evaluated | blocked
```

There is no reverse transition and no terminal rewrite API.

1. Duplicate selectors may return the same run; correctness does not depend on
   a lease.
2. The first evaluator obtains the run lock, reloads state, inserts only absent
   candidate horizons, conditionally updates pending benchmarks, and commits.
3. A concurrent or retried evaluator obtains the lock later and observes the
   winner. Existing horizons are skipped, conflict inserts are ignored, and a
   benchmark update whose status is no longer pending affects zero rows.
4. With unchanged evidence, the handled run drops out of the due predicate.

Therefore the business state satisfies `E_w(E_w(S)) = E_w(S)`. Separate
TaskRun attempts remain valid audit events; `TaskRun` itself has no uniqueness
constraint (`packages/domain/models.py:1185-1208`) and does not need one for
domain correctness.

Selection and evaluation are intentionally not atomic. If a bar disappears or
is replaced between them, the evaluator rechecks authoritative evidence. It
either makes a valid terminal transition or leaves the run due/not-due for a
later invocation. No stale selector projection is written.

### No-progress invariant

For observability, compare the selected reason with the post-evaluation
payload/state:

- `candidate_terminal` should create at least one previously absent terminal
  row unless another worker won the race;
- `benchmark_repair` should move at least one pending benchmark to evaluated or
  blocked unless another worker won the race.

A zero-transition result is a normal `concurrent_reuse` when a reload shows the
work already terminal. Otherwise record a bounded `DUE_RUN_NO_PROGRESS`
diagnostic. Do not loop on the same run again inside one batch.

## Index recommendations

Existing indexes already support the candidate lane:

- bars use primary key `(instrument_id, trade_date)`
  (`packages/domain/models.py:197-203`);
- candidates index `run_id` (`packages/domain/models.py:786-790`);
- outcomes have unique `(candidate_id, horizon_sessions)` plus a candidate ID
  index (`packages/domain/models.py:859-866,996-1001` and
  `alembic/versions/0021_research_shortlist_outcomes.py:245-249`);
- runs have the market/profile/date latest index
  (`packages/domain/models.py:689-703`).

The benchmark lane lacks an index beginning with benchmark state. If real
backlog `EXPLAIN` shows a scan, add a portable composite index:

```text
(benchmark_status, status, maturity_trade_date, candidate_id)
```

or, on PostgreSQL, the smaller partial index:

```sql
CREATE INDEX ix_research_outcomes_pending_benchmark
ON research_candidate_outcomes (maturity_trade_date, candidate_id)
WHERE status = 'evaluated' AND benchmark_status = 'pending';
```

Do not add both without measured need. Do not query JSON diagnostics to infer
due state; status, dates, canonical identity, and exact bars are the contract.

## TaskRun result and lineage

Keep result JSON bounded and explicit:

```json
{
  "selected_run_count": 8,
  "candidate_due_run_count": 6,
  "benchmark_due_run_count": 3,
  "processed_run_count": 8,
  "succeeded_run_count": 7,
  "failed_run_count": 1,
  "concurrent_reuse_count": 0,
  "remaining_due_estimate": null,
  "selected_run_ids": ["..."],
  "failures": [{"run_id": "...", "code": "OUTCOME_EVALUATION_FAILED"}]
}
```

Cap run IDs and failures to the batch limit, cap error text separately, and do
not claim an exact remaining count unless an explicit count query is worth its
cost. `has_more` can be derived by selecting one sentinel run beyond the limit.

Passing the orchestration TaskRun ID records lineage only for newly inserted
candidate terminal rows. Benchmark-only enrichment currently updates benchmark
fields without changing `evaluation_task_run_id`
(`packages/services/research_shortlist_outcomes.py:923-939`). Do not overwrite
the original candidate-evaluation lineage. Record benchmark-repaired run/outcome
IDs in the current TaskRun result. If durable reverse lineage for benchmark
completion becomes mandatory, add a separate
`benchmark_completion_task_run_id`; do not repurpose the existing field.

## Required boundary tests

### Selector truth table

- 4/5, 19/20, and 59/60 completed bars: not due.
- Exact 5th, 20th, or 60th completed bar: candidate terminal due.
- Same-day pre-16:00/incomplete rows: do not advance readiness.
- Missing entry plus N completed forward bars: due, then terminal blocked.
- Inactive/delisted candidate: not filtered; its own bars control readiness.
- Same instrument in two cohorts: independent due dates from candidate entry.
- Existing terminal row: not candidate due even if bars were later replaced.
- Sixty bars with all three rows absent: one run selected once; one evaluator
  call materializes all ready horizons.

### Benchmark lane

- Canonical instrument absent: benchmark pending but not due.
- Canonical instrument exists but entry or maturity date is missing/incomplete:
  not due.
- Both exact completion-eligible bars exist: benchmark repair due.
- Exact rows have invalid price or mixed/unknown adjustment: still due; one
  evaluator call freezes benchmark blocked, then it is no longer due.
- Stock symbol `000300`: never satisfies canonical identity.
- A run due in both lanes: returned and evaluated once.
- Stale pending diagnostics or nullable stored benchmark instrument ID do not
  affect selection.

### Batching and concurrency

- `run_limit` lower/upper validation and hard maximum.
- More due runs than the limit: deterministic oldest subset; a second call
  after processing returns the next subset without OFFSET state.
- Crash after K commits: those K disappear; untouched runs remain due.
- One run exception rolls back that run and does not prevent later selected
  runs from completing.
- Two workers select the same IDs: final candidate row count remains one per
  `(candidate,horizon)` and benchmark makes at most one terminal transition.
- A selector/evaluator race that removes evidence produces no fabricated row.
- Query count remains constant with candidate count; returned/materialized rows
  satisfy the per-run and per-batch bounds.
- No provider adapter, fallback payload service, or network client is called.

## Implementation boundaries

- Keep due predicates and batching in
  `packages/services/research_shortlist_outcomes.py`; workers call the service
  and must not reproduce SQL or horizon math.
- Reuse `_resolve_as_of`, `_completed_bar_predicate`, `OUTCOME_HORIZONS`, and
  the existing evaluator. Do not create a second completed-day or adjustment
  implementation.
- Keep Celery wrapper, progress heartbeat, TaskRun lifecycle, and schedule in
  their existing worker/dispatch layers. The service remains framework-neutral.
- Do not add a due queue table or claim/lease columns for V1. The monotone
  domain transitions, deterministic selector, and bounded retries already make
  duplicate delivery safe.
- Do not lower 95/90/80 publication thresholds, fetch benchmark/provider data,
  or feed outcome values back into shortlist scoring.
