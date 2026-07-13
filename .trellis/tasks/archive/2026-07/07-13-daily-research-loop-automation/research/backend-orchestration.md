# Backend orchestration research

## Scope

This note evaluates the smallest reliable backend architecture for automating
the daily A-share research loop:

1. publish one immutable daily research shortlist from completed local evidence;
2. mature due 5/20/60-session observations for previously published cohorts;
3. expose auditable execution state through the existing TaskRun operations
   surface;
4. preserve the existing research-only, no-trading boundary.

The recommendation intentionally does not make the research task responsible
for fetching provider data or repairing evidence. Evidence backfills remain a
separate upstream operation.

## Executive recommendation

Add one Celery task named `research.run_daily_research_loop`, backed by one
service-layer orchestrator. Do not use a Celery chain and do not schedule
shortlist generation and outcome maturation as unrelated tasks.

The worker should:

1. resolve a verified local daily-bar completed-through watermark;
2. defer without publishing when an A-share evidence backfill is active or no
   trustworthy watermark exists;
3. evaluate bounded batches of genuinely due historical cohorts through the
   existing outcome service;
4. generate the current shortlist through the existing generation service with
   an internal completed-through cutoff;
5. record progress and the final structured result in one TaskRun.

This is the minimum architecture that keeps one operational unit while reusing
the idempotency and concurrency guarantees already implemented at both domain
boundaries.

## Existing primitives

### TaskRun lifecycle and operations

`packages/services/task_runs.py` already provides the required lifecycle:

- `start_task_run()` creates and commits a running row with an initial
  heartbeat (`packages/services/task_runs.py:49`).
- `finish_task_run()` records a succeeded terminal state and result payload
  (`packages/services/task_runs.py:64`).
- `update_task_run_progress()` bounds counters, updates the heartbeat, and
  stores progress under `result_json.progress`
  (`packages/services/task_runs.py:76`).
- `fail_task_run()` records a failed terminal state and error
  (`packages/services/task_runs.py:106`).
- `expire_stale_task_runs()` uses the latest heartbeat, falling back to
  `started_at`, to expire abandoned work (`packages/services/task_runs.py:117`).
- `enqueue_task_run()` creates the row before dispatch and records the Celery
  task ID (`packages/services/task_runs.py:133`).
- `retry_task_run_payload()` creates a new auditable run and adds `retry_of` to
  the original input (`packages/services/task_runs.py:215`).

The model already stores all required generic lineage fields without a new
table: task name, status, input/result JSON, error, Celery ID, timestamps, and
heartbeat (`packages/domain/models.py:1185`).

The existing operational API is sufficient:

- `GET /task-runs/recent`
- `GET /task-runs/latest?task_name=...`
- `GET /task-runs/{id}`
- `POST /task-runs/{id}/retry`

These routes are implemented in `apps/api/routers/task_runs.py:12-45`. A
dedicated daily-loop status API would duplicate this surface and is not needed
for V1.

### Worker wrapper convention

Existing report workers establish the local convention:

1. open `SessionLocal`;
2. reuse `task_run_id` when supplied, otherwise start a TaskRun;
3. call service-layer behavior;
4. finish on success;
5. fail and re-raise on error;
6. close the session in `finally`.

See `apps/worker/tasks/reports.py:21-74` and
`apps/worker/tasks/reports.py:99-163`. The corresponding failure and TaskRun
reuse contracts are covered in `tests/worker/test_tasks.py:558-612`.

The new worker should follow this pattern exactly rather than embedding domain
queries or commits in the Celery wrapper.

### Celery Beat and dispatch

Celery is explicitly configured for `Asia/Shanghai` with UTC enabled
(`apps/worker/celery_app.py:13-15`). Existing A-share evidence jobs run at
18:30 and 20:30 on weekdays (`apps/worker/celery_app.py:70-85`).

`packages/services/task_dispatch.py:151-174` owns the dispatch registry. Adding
one dispatcher entry makes the existing TaskRun retry endpoint work for the
daily loop without a new retry implementation.

### Shortlist generation

`generate_research_shortlist()` is the sole generation boundary
(`packages/services/research_shortlists.py:114-161`). It already:

- normalizes the profile and criteria;
- resolves a decision date from local daily bars;
- checks 95/90/80 evidence coverage;
- performs point-in-time local screening;
- validates exact decision-date entry bars;
- freezes the immutable run and candidates;
- falls back safely when explanation generation cannot be trusted.

Its deterministic generation key includes market, asset type, profile,
normalized criteria, decision date, methodology IDs, and shortlist limit
(`packages/services/research_shortlists.py:425-451`). PostgreSQL advisory locks,
SQLite process locks, and the unique generation key make repeated or concurrent
calls converge on one committed run (`packages/services/research_shortlists.py:980-1033`).

One narrow gap matters for automation: `_latest_decision_date()` currently
selects the global maximum stored trade date with no completed-through upper
bound (`packages/services/research_shortlists.py:926-939`). A partial or
intraday row could therefore move automated generation beyond the trusted
watermark.

### Outcome maturation

`evaluate_research_shortlist_outcomes()` already exposes the correct internal
worker contract (`packages/services/research_shortlist_outcomes.py:91-166`):

- explicit `verified_completed_through`;
- optional `evaluation_task_run_id` lineage;
- local database evidence only;
- completed-bar filtering;
- strict 5/20/60 horizons;
- candidate terminal immutability;
- independent one-way benchmark enrichment;
- per-run locking and conflict-safe inserts.

The automation must call this function. It must not duplicate horizon math or
write `ResearchCandidateOutcome` directly.

Calling it only for the latest shortlist is incorrect: a newly published cohort
is pending, while prior cohorts become due on later dates. The automation needs
a due-cohort selector across all committed runs in the selected CN stock
profile.

### Evidence backfill state

`ResearchEvidenceBackfill` already stores the fields needed to derive a
watermark: market, provider, run kind, status, evidence kinds, scope, start/end
dates, progress, heartbeat, and finished time
(`packages/domain/models.py:114-193`).

A completed execution records `status=succeeded|partial`, `finished_at`, and
the frozen `end_date` (`packages/services/research_evidence_backfill.py:656-670`).
The active states are `queued`, `running`, and `cancel_requested`
(`packages/services/research_evidence_backfill.py:51`), and the current active
lookup is at `packages/services/research_evidence_backfill.py:771-783`.

Scheduled backfill orchestration in `apps/worker/tasks/ingestion.py:574-619`
is useful as a pattern, but the daily research task must not create another
backfill. Starting providers from this task would couple publication to repair,
break the single-AkShare-run operational rule, and make retries ambiguous.

## Proposed components

### 1. Verified watermark resolver

Add a public service function in
`packages/services/research_evidence_backfill.py`, for example:

```python
resolve_completed_daily_bar_watermark(
    *,
    session: Session,
    now: datetime | None = None,
) -> CompletedDailyBarWatermark | None
```

The returned value should contain at least:

- `completed_through`;
- source backfill run ID;
- source TaskRun ID when present;
- source status and finished timestamp.

A run is eligible only when all of the following are true:

- `market=CN`;
- `provider=akshare`;
- `run_kind` is `baseline` or `incremental` (a resumed run retains that kind);
- `evidence_kinds_json` contains `daily_bars`;
- status is terminal `succeeded` or `partial`;
- `finished_at` is non-null;
- `end_date` is not in the future.

Do not accept these as a market-wide watermark:

- `canary`, because it covers only a sample;
- `fundamental_shard`, because it does not refresh daily bars;
- `retry_failed`, because it covers only retry symbols;
- queued, running, cancel-requested, cancelled, or failed runs.

A `partial` full-scope run may establish that the processing window ended, but
it does not waive coverage. Shortlist generation must still pass the existing
95/90/80 gate, and outcome evaluation still applies the per-bar completion
rule. If policy prefers a stricter initial rollout, accepting only `succeeded`
is safe but may defer publication for a small retry set even when coverage is
otherwise sufficient.

For a current-Shanghai-date watermark, require local time at or after 16:00.
This mirrors the outcome service contract. The per-bar `ingested_at` rule remains
authoritative and cannot be bypassed by the watermark.

Before using a terminal watermark, check whether any CN/AkShare evidence
backfill is active. If so, defer the loop to avoid screening while evidence is
being replaced. The existing `_active_backfill()` lookup should become a
public read helper instead of being imported as a private function.

The active check is an operational gate, not a concurrency lock. Correctness
must continue to depend on the explicit cutoff and the shortlist/outcome domain
locks.

### 2. Internal generation cutoff

Extend the service input with an internal-only cutoff, for example:

```python
@dataclass(frozen=True)
class ResearchShortlistGenerateInput:
    # existing fields...
    completed_through: date | None = None
```

When set, `_latest_decision_date()` must add:

```python
DailyBar.trade_date <= completed_through
```

Do not add this field to `ResearchShortlistGenerateRequest`; browsers cannot
assert a trusted watermark. Manual generation behavior and existing API
contracts remain unchanged.

After choosing the latest local decision date at or below the cutoff, the
existing implementation already passes that date to coverage and screening
(`packages/services/research_shortlists.py:177-197`). No additional scoring or
selection path is needed.

The automation must not retrospectively create cohorts for historical dates
that were never published point in time. A retry for the same daily slot may
publish the current intended date, but a later day's run should not backfill a
missed historical shortlist from revised evidence.

### 3. Due-cohort selector and evaluator

Expose a service-layer batch entry point in
`packages/services/research_shortlist_outcomes.py`, for example:

```python
evaluate_due_research_shortlist_outcomes(
    *,
    session: Session,
    market: str,
    profile_id: str,
    completed_through: date,
    evaluation_task_run_id: UUID,
    run_limit: int = 100,
) -> dict[str, object]
```

It should select a run only when at least one operation can make progress:

1. a candidate/horizon has no terminal row and at least N completed forward
   bars exist through the cutoff; or
2. an evaluated candidate has `benchmark_status=pending` and the canonical
   benchmark now has valid exact entry and maturity-date bars.

Do not repeatedly select every benchmark-pending run while the canonical
instrument or exact bars remain absent. That would turn an honest missing
benchmark into permanent daily no-op work.

Selection must remain scoped to committed `CN/stock` runs for the configured
profile. Process bounded batches and order deterministically. Oldest due first
is reasonable because successful terminal writes naturally remove work from
the queue, preventing starvation without a new cursor table. Inactive or
delisted candidates remain in the cohort; they simply do not become due until
their own completed-bar count reaches the horizon.

For every selected run, call the existing
`evaluate_research_shortlist_outcomes()` with:

- `as_of=completed_through`;
- `verified_completed_through=completed_through`;
- the same orchestration TaskRun ID as `evaluation_task_run_id`.

Catch and record a failure per run, roll back the session, then continue other
due runs. A malformed or temporarily problematic old cohort must not block all
other maturation or current shortlist publication.

The result should report due, processed, succeeded, and failed run counts plus
aggregate evaluated/blocked/pending counts. Failure diagnostics must be
structured and bounded.

### 4. Daily loop service

Add `packages/services/daily_research_loop.py` with a framework-neutral entry
point:

```python
run_daily_research_loop(
    payload: DailyResearchLoopInput,
    *,
    session: Session,
    task_run_id: UUID,
    now: datetime | None = None,
) -> dict[str, object]
```

Suggested input fields:

- `market="CN"`;
- `profile_id="balanced_research"`;
- `asset_type="stock"`;
- `shortlist_limit=10`;
- `locale="zh"`;
- `use_llm=True`.

The service should execute two independent phases after resolving the
watermark:

1. mature due historical outcomes;
2. generate or reuse the current shortlist at or before the watermark.

The phases must be independently degradable. Per-run outcome errors should not
prevent generation. A generation readiness gate should not discard outcomes
already matured in the same invocation.

The service should call `update_task_run_progress()` at phase boundaries and
during bounded outcome batches so a legitimate long run remains healthy.

### 5. Celery worker, dispatcher, and Beat

Add `apps/worker/tasks/research.py`:

```python
@celery_app.task(name="research.run_daily_research_loop")
def run_daily_research_loop_task(..., task_run_id: str | None = None):
    ...
```

The wrapper should follow the existing report-task lifecycle exactly. It must
reuse a supplied TaskRun, create one for a direct Beat invocation, finish on
successful or expected-deferred completion, fail and re-raise unexpected
errors, and always close its session.

Add `_dispatch_daily_research_loop()` and one registry entry in
`packages/services/task_dispatch.py`. This makes the existing retry API work
without special routing.

Register/import the module from `apps/worker/celery_app.py` and add one
configurable weekday Beat entry after the existing evidence windows. A late
Shanghai-evening schedule is the smallest rollout. Fixed time is not a data
dependency, so the active-backfill/watermark gate remains mandatory.

Do not use Celery `autoretry_for` in V1. The repository has no established
autoretry lifecycle, and a readiness gate is not a transient exception. The
existing TaskRun retry endpoint creates a new auditable run, while the next
Beat invocation safely rechecks the local state.

## Execution flow

```text
Celery Beat / TaskRun retry
          |
          v
research.run_daily_research_loop worker
          |
          +--> load/reuse TaskRun
          |
          +--> resolve active backfill + verified watermark
          |        |
          |        +--> unavailable/active -> finish TaskRun as deferred
          |
          +--> evaluate bounded due cohorts
          |        +--> existing outcome service per run
          |        +--> record per-run failures and continue
          |
          +--> generate/reuse shortlist <= watermark
          |        +--> existing readiness thresholds
          |        +--> existing generation lock/key
          |
          +--> finish or fail TaskRun with structured result
```

## Failure semantics

| Condition | TaskRun terminal state | Daily-loop result | Behavior |
|---|---|---|---|
| Active evidence backfill | `succeeded` | `deferred` | Publish nothing; report active run ID |
| No verified watermark | `succeeded` | `deferred` | Publish nothing; report structured code |
| `ResearchShortlistReadinessError` | `succeeded` | `deferred` or `completed_with_deferred_generation` | Keep thresholds and prior shortlist unchanged |
| No due outcomes | `succeeded` | `completed` | Generation may still run |
| One due cohort fails | `failed` after remaining work | `partial_failure` | Continue other cohorts and generation, preserve partial result, then fail/re-raise |
| Unexpected DB/code error | `failed` | `failed` | Preserve bounded partial result, fail and re-raise |
| Duplicate invocation/retry | independent TaskRun rows allowed | same domain result | Domain locks/unique keys prevent duplicate publication or outcomes |

Before `fail_task_run()`, assign the bounded partial orchestration result to
`task_run.result_json`. `fail_task_run()` does not clear that field, so operators
can inspect completed phases while TaskRun and Celery both correctly show
failure.

Expected readiness conditions should not be reported as failed TaskRuns. Doing
so would make the existing health tooling warn every time coverage is honestly
below threshold.

## Idempotency and concurrency

No new orchestration table is required.

- Shortlist generation is idempotent by deterministic generation key and its
  existing database/process lock.
- Candidate outcomes are idempotent by `(candidate_id, horizon)` uniqueness,
  run-scoped locks, and conflict-safe inserts.
- Benchmark enrichment is a conditional one-way transition.
- Reusing the same cutoff and profile therefore produces the same business
  state even when Beat delivery, a worker retry, and a manual TaskRun retry
  overlap.
- Separate TaskRun rows are acceptable and useful audit records. Avoid adding a
  TaskRun uniqueness migration solely to hide duplicate deliveries.

The daily-loop service must not hold an outer transaction across both phases.
The reused domain services own their commits and locks. A single all-or-nothing
transaction would make long execution fragile and would undo already valid
cohort maturation when unrelated generation is deferred.

## Result contract

A useful bounded `TaskRun.result_json` shape is:

```json
{
  "status": "completed",
  "completed_through": "2026-07-13",
  "watermark": {
    "backfill_run_id": "...",
    "task_run_id": "...",
    "status": "succeeded",
    "finished_at": "..."
  },
  "outcomes": {
    "due_run_count": 4,
    "processed_run_count": 4,
    "succeeded_run_count": 4,
    "failed_run_count": 0,
    "evaluated_count": 12,
    "blocked_count": 0,
    "pending_count": 108,
    "failures": []
  },
  "shortlist": {
    "status": "available",
    "run_id": "...",
    "decision_date": "2026-07-13",
    "item_count": 10,
    "diagnostics": []
  },
  "research_signal_only": true,
  "safety": {
    "no_automated_trading": true,
    "outcomes_do_not_change_shortlist_ranking": true
  }
}
```

Do not place provider payloads, credentials, LLM prompts, or unbounded exception
text in TaskRun JSON. Failure arrays and diagnostics need explicit caps.

## Test matrix

### Watermark and readiness

- Ignore active, failed, cancelled, and cancel-requested runs.
- Ignore canary, fundamental shard, and retry-failed runs.
- Accept a finished full-scope daily-bar baseline/incremental run.
- Cover the chosen policy for `partial` full-scope runs.
- Choose the greatest eligible `end_date`, then latest finish time.
- Reject a future watermark and the current Shanghai date before 16:00.
- Defer when any CN/AkShare backfill is active.
- Verify no provider/network function is called.

### Generation cutoff and idempotency

- Seed a trusted prior-day watermark plus a later intraday row; automated
  generation must choose a decision date no later than the watermark.
- Repeated and concurrent loop invocations return the same shortlist run ID.
- Coverage not ready produces a deferred TaskRun result and creates no new run.
- Preserve the 95/90/80 thresholds and existing safety payload.
- Prove the public FastAPI request cannot set `completed_through`.

### Due outcome maturation

- Seed multiple historical cohorts so 5, 20, and 60 mature on different runs;
  prove the selector does not process only latest.
- A run with fewer than N completed bars is not selected for that missing
  horizon.
- Inactive/delisted candidates remain in cohort accounting without blocking
  other due candidates.
- Missing canonical benchmark data does not repeatedly select a no-op run.
- Exact benchmark entry/exit rows make one pending benchmark enrichment due.
- Pass the orchestration TaskRun ID into persisted outcome lineage.
- One cohort failure does not prevent other cohorts or generation.
- Repeated/concurrent evaluation creates one terminal row per
  candidate/horizon and does not rewrite terminal values.
- Assert all provider/network adapters remain unused.

### Worker, dispatch, and schedule

- Direct Beat invocation creates and finishes one TaskRun.
- A dispatched invocation reuses the supplied TaskRun.
- Progress updates refresh the heartbeat.
- Deferred, successful, partial-failure, and unexpected-failure paths persist
  the expected result and status.
- Unexpected failure calls `fail_task_run`, re-raises, and closes the session.
- Dispatcher forwards all configuration and `task_run_id`.
- TaskRun retry adds `retry_of` and converges on the same domain result.
- Beat uses the expected task name, weekday schedule, kwargs, and Shanghai
  timezone.
- Existing TaskRun latest/detail/recent/retry API tests include the new task.

### Operations and long-run health

`expire_stale_task_runs()` correctly honors `heartbeat_at`, but
`scripts/task_run_health.py` currently identifies stale running work using only
`started_at`. A daily loop with a large outcome backlog could therefore be
healthy according to the API and falsely WARN in the CLI.

Before treating the loop as potentially long-running, align the diagnostic
script with the runtime predicate and add a regression for an old
`started_at` plus a fresh heartbeat.

## Main risks and decisions

1. **Fixed Beat time is not an evidence dependency.** Keep the active-run and
   watermark gate even when scheduling late in the evening.
2. **Latest-only outcome evaluation is functionally wrong.** Historical due
   cohorts need explicit selection.
3. **A watermark without a generation cutoff is ineffective.** The current
   max-bar decision-date query must be bounded internally.
4. **Benchmark absence can create permanent no-op work.** Revisit pending
   benchmarks only when exact local evidence can progress them.
5. **Do not lower coverage to make automation green.** Readiness is an honest
   deferred result, not a reason to change 95/90/80.
6. **Do not start providers from the loop.** Backfill, publication, and outcome
   observation remain separate operational responsibilities.
7. **Do not add portfolio/backtest semantics.** Automation publishes and
   observes research signals only; outcomes never alter ranking or future
   membership.

## Expected implementation surface

The minimal affected files are:

- `packages/services/research_evidence_backfill.py`
- `packages/services/research_shortlists.py`
- `packages/services/research_shortlist_outcomes.py`
- `packages/services/daily_research_loop.py` (new)
- `packages/services/task_dispatch.py`
- `apps/worker/tasks/research.py` (new)
- `apps/worker/tasks/__init__.py`
- `apps/worker/celery_app.py`
- `packages/shared/config.py`
- focused service/worker/dispatch/schedule/TaskRun API tests
- optionally `scripts/task_run_health.py` and its tests for heartbeat parity

No new domain table or dedicated HTTP status endpoint is required for V1.
