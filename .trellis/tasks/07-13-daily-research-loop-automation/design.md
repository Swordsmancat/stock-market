# Daily research loop automation - design

## Product boundary

The automation is a scheduler and evidence gate around two existing domain
services. It turns completed local evidence into a repeatable daily research
artifact and follow-up observations. It never fetches evidence, changes scoring
rules, learns from outcomes, constructs a portfolio, or emits a trade action.

## Architecture

Use one Celery orchestration task and the existing generic TaskRun operations
surface:

```text
Celery Beat / TaskRun retry
          |
          v
research.run_daily_research_loop
          |
          +--> active backfill gate
          +--> trusted completed daily-bar watermark
          +--> bounded due-cohort evaluation
          +--> current shortlist generate/reuse
          +--> TaskRun progress + structured terminal result
```

The worker owns session and TaskRun lifecycle. A framework-neutral service owns
phase ordering and accepts a progress callback. Existing shortlist and outcome
services retain their own commits, locks, and immutable identities; the daily
loop does not hold one outer transaction across phases.

## Shared completed-bar contract

Move the SQL and Python daily-bar completion predicates into one small service
module used by both outcome evaluation and watermark resolution. Preserve the
existing dialect semantics:

- SQLite treats stored naive timestamps as UTC and compares
  `datetime(ingested_at)` to `datetime(trade_date, '+8 hours')`;
- PostgreSQL compares `ingested_at` to 16:00 Asia/Shanghai on `trade_date`
  independently of the database session timezone;
- unsupported dialects fail explicitly;
- the in-memory check converts aware or naive-as-UTC timestamps to Shanghai.

This avoids two implementations of the most important trust boundary.

## Watermark resolution

Add public read helpers beside the backfill service:

```python
get_active_research_evidence_backfill(*, session, market="CN", provider="akshare")

resolve_completed_daily_bar_watermark(
    *, session, market="CN", provider="akshare", now=None
) -> dict[str, object]
```

The resolver never calls providers. It performs these steps:

1. Return `deferred/ACTIVE_EVIDENCE_BACKFILL` with sanitized active-run identity
   when any CN/AkShare backfill is active.
2. Load finished `baseline|incremental` runs containing `daily_bars`, with
   `status in {succeeded, partial}` and non-null `finished_at`. Exclude future
   ranges, canary, fundamental-shard, retry-failed, failed, cancelled, and
   active rows.
3. Use eligible run ranges only as provenance bounds. Find recent distinct
   stored stock trade dates within those bounds, capped at the current Shanghai
   date (or previous date before 16:00).
4. Join the current active CN stock universe and apply the shared completed-bar
   predicate. Aggregate exact-date distinct instrument coverage and exchange
   representation in bounded queries.
5. Choose the latest date whose ready ratio is at least the unchanged daily-bar
   threshold `0.95` and whose ready set includes SSE, SZSE, and BSE.
6. Attach the newest eligible backfill whose range contains the selected date,
   plus its TaskRun ID, status, finish time, exact ready/total counts, ratio,
   exchange counts, timezone, evaluation time, and structured diagnostics.

The resolver returns `ready`, `not_ready`, or `no_data`. A `partial` run is
allowed to provide provenance because the exact-date coverage check remains the
authority; partial status never lowers the threshold.

The watermark proves only completed daily bars. Shortlist generation still
calls the existing point-in-time coverage service, so critical indicators and
fundamentals continue to enforce 90% and 80%. This separation lets outcomes
mature from valid bars even when publication evidence is not ready.

## Shortlist cutoff and lineage

Extend `ResearchShortlistGenerateInput` with two internal-only fields:

- `verified_decision_date: date | None`;
- `generation_task_run_id: str | UUID | None`.

The FastAPI request model remains unchanged. When a verified date is present,
generation uses that exact date instead of re-reading a global max bar. Manual
calls preserve current behavior. Normalize and validate optional TaskRun UUID
inside the service.

Revision `0022_research_shortlist_task_run` adds nullable
`research_shortlist_runs.generation_task_run_id`, an index, and a foreign key to
`task_runs.id` with `ON DELETE SET NULL`. Existing rows remain null. The field is
set only when the run is first inserted; generation-key reuse never rewrites it.
Latest/detail serialization exposes the nullable ID.

## Due-cohort selection

Add a public batch service around the existing per-run evaluator:

```python
evaluate_due_research_shortlist_outcomes(
    *, session, market, profile_id, verified_completed_through,
    evaluation_task_run_id, run_limit=25, now=None
) -> dict[str, object]
```

Candidate-terminal due selection uses three literal indexed probes combined in
one bounded query:

1. for each literal horizon 5, 20, and 60, probe the Nth completed forward bar
   after the candidate entry date through the verified cutoff;
2. scope to committed CN stock shortlist runs for the configured profile;
3. select a run when a missing 5, 20, or 60 terminal row has reached its count;
4. order by decision date and generation time oldest first, then limit.

Use correlated `ORDER BY trade_date OFFSET N-1 LIMIT 1` probes and
`NOT EXISTS` outcome checks, then `UNION ALL` the three literal horizons. This
lets the daily-bar primary key stop at N instead of counting or materializing
all later history. A missing entry bar does not exclude a due candidate: once N
forward bars exist, the evaluator must be allowed to freeze
`ENTRY_BAR_MISSING` rather than leave the item pending forever.

Benchmark enrichment is optional and second priority. Select an evaluated
outcome with `benchmark_status=pending` only when the canonical
`CN/index/cn_csi_300` instrument exists and exact completed bars are present for
both candidate entry and stored maturity date. Fill only the remaining run
budget and exclude IDs already selected for candidate work. Invalid price or
adjustment can still be selected because the existing evaluator must freeze the
structured benchmark-blocked result; missing exact evidence is not selected.

For each run, invoke `evaluate_research_shortlist_outcomes()` with the same
verified date as both `as_of` and `verified_completed_through`, and pass the
current orchestration TaskRun ID. Catch exceptions per run, roll back the
session, retain exception type plus a bounded generic diagnostic, continue, and
return a bounded failure list. Do not call a private outcome writer.

The batch payload reports candidate-due, benchmark-due, considered, processed,
succeeded, and failed run counts; processed run IDs; failure records; and final
evaluated/blocked/pending horizon counts from each returned run. Count names
must distinguish final observed state from newly inserted rows.

Refactor the evaluator's canonical benchmark loader to query only required
exact dates: candidate entry dates, existing pending outcome maturity dates,
and newly visible 5/20/60 maturity dates from the bounded candidate windows.
Do not load the entire index date range from the oldest cohort to the cutoff.
Select one sentinel beyond `run_limit` for `has_more`; do not add an offset or
durable queue cursor. If selected work produces no transition and another
worker did not already finish it, emit bounded `DUE_RUN_NO_PROGRESS` once and
do not loop over it again in the same batch.

Terminal outcome serialization adds nullable `evaluation_task_run_id`.
Derived pending horizons emit null. Benchmark enrichment keeps the row's
original candidate evaluation lineage because it does not rewrite immutable
candidate evaluation provenance.

## Daily loop service

Add `packages/services/daily_research_loop.py`:

```python
@dataclass(frozen=True)
class DailyResearchLoopInput:
    market: str = "CN"
    asset_type: str = "stock"
    profile_id: str = "balanced_research"
    shortlist_limit: int = 10
    locale: str = "zh"
    use_llm: bool = True
    outcome_run_limit: int = 25

run_daily_research_loop(
    payload, *, session, task_run_id, now=None, progress=None
) -> dict[str, object]
```

Normalize the same fixed CN/stock boundary and bounds `1..20` shortlist,
`1..100` outcome runs. Sequence:

1. report watermark progress;
2. resolve active gate and watermark;
3. return successful `deferred` when not ready;
4. evaluate due historical outcomes, preserving per-run failures;
5. generate/reuse the current shortlist with verified date and TaskRun lineage;
6. turn `ResearchShortlistReadinessError` into
   `completed_with_deferred_generation` without lowering thresholds;
7. report completion and return structured safety metadata.

Generation response status is classified as `created` when the run's original
generation TaskRun equals the current TaskRun and `reused` otherwise. The
TaskRun result records both original lineage and current reuse.

If due-cohort failures exist, finish all possible phases and return
`partial_failure`. The worker persists that result and raises a dedicated
bounded exception so TaskRun and Celery correctly fail. Other unexpected
exceptions propagate immediately after the worker preserves available partial
progress.

## Worker, dispatch, and schedule

Add `apps/worker/tasks/research.py` using the established wrapper:

1. open `SessionLocal`;
2. reuse a supplied TaskRun or create one for direct Beat delivery;
3. call the service with a progress callback backed by
   `update_task_run_progress()`;
4. finish expected `completed`, `completed_with_deferred_generation`, or
   `deferred` results;
5. before raising on `partial_failure`, persist the bounded result;
6. on any exception, call `fail_task_run()` and re-raise;
7. always close the session.

Register the task in `task_dispatch.py` and the synchronous test dispatcher.
Retry forwards stable input fields plus the pre-created TaskRun ID; unknown
extra `retry_of` remains only in TaskRun input and does not alter domain input.

Add settings:

- `daily_research_loop_enabled=true`;
- `daily_research_loop_cron_hour=21`;
- `daily_research_loop_cron_minute=30`;
- `daily_research_loop_outcome_run_limit=25`.

When enabled, Celery Beat schedules weekdays with stable CN/balanced/default
kwargs. The watermark gate, not the clock, decides readiness. Do not add Celery
autoretry or invoke evidence ingestion.

## TaskRun health parity

`expire_stale_task_runs()` already uses `heartbeat_at` with `started_at`
fallback. Align `scripts/task_run_health.py` to the same predicate so a healthy
long loop with an old start and fresh heartbeat is not reported stale. The
script remains read-only and keeps current OK/WARN exit semantics.

## Result and failure contract

The result is bounded and structured:

```json
{
  "status": "completed",
  "watermark": {
    "status": "ready",
    "verified_completed_through": "2026-07-13",
    "backfill_run_id": "...",
    "backfill_task_run_id": "...",
    "exact_date_ready_count": 5200,
    "active_count": 5400,
    "coverage_ratio": 0.9629
  },
  "outcomes": {
    "candidate_due_run_count": 2,
    "benchmark_due_run_count": 1,
    "processed_run_count": 3,
    "failed_run_count": 0,
    "failures": []
  },
  "publication": {
    "status": "created",
    "shortlist_run_id": "...",
    "generation_task_run_id": "...",
    "decision_date": "2026-07-13",
    "item_count": 10
  },
  "research_signal_only": true,
  "safety": {
    "no_automated_trading": true,
    "outcomes_do_not_change_shortlist_ranking": true
  }
}
```

Expected gate failures use stable codes and a succeeded TaskRun. Unexpected
errors store no raw provider response, credentials, prompt, or unbounded
exception text. Failure arrays have an explicit cap.

## Frontend and API compatibility

No new public automation API or page is added. Existing TaskRun recent/detail
pages display generic input/result JSON and already expose retry. Existing AI
Research panels remain independently degradable. Adding lineage fields is an
additive response change; no browser request can supply trusted watermark or
lineage values.

## Rollout and rollback

- Migration rollback drops the index, constraint, and nullable column only;
  shortlist and outcome rows remain.
- Disable the Beat entry with `DAILY_RESEARCH_LOOP_ENABLED=false` without
  removing manual generation/evaluation.
- Removing the worker/service/dispatch entry restores manual-only operation.
- A deferred loop never mutates domain state. Already committed shortlist and
  outcome rows remain valid after worker rollback.

## Main risks

- Fixed schedule may overlap a long fundamental shard; active-backfill gating
  intentionally defers rather than reading a moving evidence set.
- Current active-universe changes can alter the exact-date denominator. This is
  conservative and auditable; the source backfill remains provenance, while
  the current active set determines publication readiness.
- Candidate-forward counting across long history can become expensive. Keep it
  in SQL, scope to committed cohorts, require the minimum 5-bar threshold, and
  protect behavior with query/selection tests.
- Missing CSI 300 can remain null indefinitely. It is not a reason to loop over
  no-op cohorts or introduce a provider inside this task.
