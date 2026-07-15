# Daily Research Loop Automation Contract

## Scenario: Trusted Daily A-share Research Orchestration

### 1. Scope / Trigger

- Trigger: completed local A-share evidence must mature due 5/20/60-session
  cohort observations before publishing or reusing one immutable daily
  shortlist.
- Scope: `packages/services/daily_bar_completion.py`,
  `packages/services/daily_research_loop.py`, the watermark and due-cohort
  helpers in `packages/services/`, `apps/worker/tasks/research.py`, generic
  TaskRun dispatch/retry, Celery Beat configuration, and Alembic revision
  `0022_research_shortlist_task_run`.
- Public UI/API scope is unchanged. Operators use the generic TaskRun
  recent/detail/retry surface and the existing AI Research panels.
- Non-goals: provider ingestion, historical shortlist reconstruction,
  backtesting, strategy optimization, portfolio construction, orders, brokers,
  or automated trading.

### 2. Signatures

- Completed-bar SQL/Python helpers:
  `completed_daily_bar_predicate(session, bar=DailyBar)` and
  `daily_bar_timestamp_is_complete(ingested_at, trade_date)`.
- Watermark:
  `get_active_research_evidence_backfill(*, session, market="CN",
  provider="akshare")` and
  `resolve_completed_daily_bar_watermark(*, session, market="CN",
  provider="akshare", now=None) -> dict[str, object]`.
- Due batch:
  `evaluate_due_research_shortlist_outcomes(*, session, market, profile_id,
  verified_completed_through, evaluation_task_run_id, run_limit=25,
  now=None, progress=None) -> dict[str, object]`.
- Orchestrator:
  `run_daily_research_loop(payload, *, session, task_run_id, now=None,
  progress=None) -> dict[str, object]`, where `payload` is
  `DailyResearchLoopInput`.
- Celery task: `research.run_daily_research_loop`.
  Worker defaults are `CN`, `stock`, `balanced_research`, shortlist limit 10,
  locale `zh`, LLM enabled, outcome limit 25, trigger `scheduled`, and an
  optional supplied `task_run_id`.
- Database: nullable
  `research_shortlist_runs.generation_task_run_id -> task_runs.id` with
  `ON DELETE SET NULL` and an index. Existing rows remain null.
- Settings/env:
  `DAILY_RESEARCH_LOOP_ENABLED`, `DAILY_RESEARCH_LOOP_CRON_HOUR`,
  `DAILY_RESEARCH_LOOP_CRON_MINUTE`, and
  `DAILY_RESEARCH_LOOP_OUTCOME_RUN_LIMIT`.

### 3. Contracts

- The watermark is local-only. It must not call a provider or network client.
  Any queued, running, or cancellation-pending CN/AkShare evidence backfill
  returns `not_ready/ACTIVE_EVIDENCE_BACKFILL`.
- Only finished `baseline|incremental` runs containing `daily_bars`, with
  status `succeeded|partial`, may bound candidate dates. Canary,
  fundamental-shard, retry-failed, failed, cancelled, and active runs cannot
  establish provenance.
- Exact-date completed bars must cover at least 95% of the current active CN
  stock universe and include nonzero SSE, SZSE, and BSE representation. The
  resolver checks only the latest 31 natural days and rejects future dates and
  the current Shanghai date before 16:00.
- A daily bar is complete when ingestion occurred at or after 16:00
  Asia/Shanghai on its trade date or on a later Shanghai date. SQLite naive
  timestamps are interpreted as UTC; PostgreSQL completion is independent of
  the database session timezone.
- The watermark proves daily-bar completion only. Shortlist publication still
  enforces the unchanged 95% daily-bar, 90% critical-indicator, and 80%
  complete-fundamental readiness thresholds.
- Due outcome work uses three literal Nth-completed-bar probes for horizons
  5, 20, and 60. Selection is oldest-first, candidate-terminal work precedes
  optional CSI 300 benchmark repair, `run_limit` is `1..100`, and a sentinel
  supplies `has_more` without an offset cursor.
- Each due run is evaluated by
  `evaluate_research_shortlist_outcomes()` with the same verified cutoff and
  current TaskRun ID. A cohort failure is rolled back, sanitized, bounded, and
  isolated while remaining cohorts and publication continue.
- Automated publication passes `verified_decision_date` and
  `generation_task_run_id` only through the internal service dataclass. The
  FastAPI request model exposes neither field. Generation-key reuse returns the
  immutable first publisher lineage and never rewrites it.
- A direct Beat delivery creates a TaskRun. Generic retry supplies a new
  running TaskRun with `retry_of`. A supplied TaskRun must belong to this task
  and be running; a succeeded replay returns its stored result unchanged, and
  other terminal states are rejected.
- Expected watermark deferral and publication-readiness deferral succeed the
  TaskRun with `deferred` or `completed_with_deferred_generation`. Isolated
  cohort failures return `partial_failure`; the worker preserves the bounded
  result, fails the TaskRun, and re-raises. Unexpected failures preserve the
  available partial phase result, fail the TaskRun, re-raise, and always close
  the worker session.
- Progress/heartbeat is updated at watermark, outcomes, publication, and
  completion boundaries. Terminal results retain the last progress payload so
  healthy long work is not classified stale.
- Beat uses `Asia/Shanghai` and runs weekdays at configurable 21:30 by default.
  The clock never bypasses the active-backfill or watermark gates, and the task
  never starts an evidence backfill or uses Celery automatic retries.
- The public `GET /task-runs/recent`, `GET /task-runs/latest`, and
  `GET /task-runs/{id}` surfaces are operational reads, not strict read-only
  diagnostics: their service path calls `expire_stale_task_runs()` and may
  transition stale `running` rows to `failed`. Acceptance or audit tooling that
  promises zero mutation must query TaskRuns inside a database
  `BEGIN READ ONLY` transaction instead.
- Every result is structured and bounded, retains
  `research_signal_only=true`, and includes `no_automated_trading=true` and
  `outcomes_do_not_change_shortlist_ranking=true`. It contains no credentials,
  prompt text, provider payloads, raw upstream responses, or unbounded
  exception strings. Selected/failure arrays are bounded by the 100-run hard
  limit; publication diagnostics are capped at 100; readiness details are
  limited to depth 5, 50 keys, 20 sampled sequence items, and 256-character
  strings/keys.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Market is not `CN`, asset type is not `stock`, or profile is empty | `ValueError`; no domain mutation |
| Shortlist limit outside `1..20` or outcome limit outside `1..100` | `ValueError`; no dispatch work |
| Invalid TaskRun UUID, wrong task name, or non-running terminal TaskRun | Reject before orchestration |
| Supplied TaskRun already succeeded with a result | Return the stored result without changing status |
| Active evidence backfill | Succeeded TaskRun with `status=deferred`; no outcomes or publication |
| No eligible backfill/universe/date | Structured `no_data` or `not_ready`, then succeeded deferred loop |
| Newer exact date has less than 95% coverage or lacks an exchange | Skip it; use an older qualifying date or defer |
| Current Shanghai date before 16:00 or any future date | Never select it as the watermark |
| Shortlist 95/90/80 readiness gate fails after outcomes | Keep matured outcomes; succeeded `completed_with_deferred_generation` |
| One or more due cohorts fail | Continue remaining work, preserve bounded failures, then fail TaskRun and re-raise |
| Unexpected watermark/outcome/publication/progress failure | Preserve bounded partial result, fail TaskRun, re-raise, close session |
| Same daily loop or retry is repeated | Reuse immutable shortlist/outcome rows; do not duplicate or revise terminal state |
| Original generation TaskRun is deleted | Shortlist lineage becomes null through `ON DELETE SET NULL` |
| A zero-mutation audit needs recent/latest TaskRun state | Use bounded `BEGIN READ ONLY` SQL; do not call the TaskRun GET API |

### 5. Good / Base / Bad Cases

- Good: the newest stored date covers 94.9%, the prior date covers exactly 95%
  across SSE/SZSE/BSE, and the loop uses the prior date for both outcome
  maturity and publication.
- Good: two old cohorts mature in one run, one benchmark remains pending, and
  the same verified date publishes one shortlist with TaskRun lineage.
- Base: completed bars are ready but indicators or fundamentals are not. Due
  outcomes commit and publication is honestly deferred without lowering
  95/90/80.
- Base: an operator needs to observe the scheduled loop without changing state.
  A bounded read-only SQL transaction returns TaskRun status/result fields and
  leaves stale-run expiration to normal operational paths.
- Base: Beat overlaps an active fundamental shard. The loop succeeds as
  deferred and performs no provider call or domain write.
- Bad: use `max(DailyBar.trade_date)` as evidence authority, accept a canary as
  full-market provenance, or treat a weekday clock as proof of completion.
- Bad: catch a cohort error and mark the whole TaskRun succeeded, overwrite the
  original shortlist publisher during reuse, or feed outcomes into later
  shortlist membership/ranking.
- Bad: label `GET /task-runs/latest` a non-mutating health probe; it can expire
  a stale running row as a side effect.

### 6. Tests Required

- Completion tests assert SQLite/PostgreSQL predicates, naive UTC handling,
  pre/post 16:00, later-day ingestion, current-day gating, and unsupported
  dialect failure.
- Watermark tests assert exact 95% boundaries, SSE/SZSE/BSE representation,
  eligible provenance kinds/statuses, active replacement deferral, 31-day
  bounds, constant query shape, and no provider access.
- Due-batch tests assert literal 5/20/60 probes, oldest-first candidate
  priority, benchmark exact-date eligibility, inactive candidates, `1..100`
  bounds, sentinel `has_more`, isolated failures, and idempotent/concurrent
  reuse.
- Shortlist/model/migration tests assert the internal verified cutoff,
  immutable generation lineage, public-request exclusion, revision `0022`
  upgrade/downgrade, the index, and `ON DELETE SET NULL`.
- Worker/dispatch tests assert direct Beat TaskRun creation, generic retry,
  succeeded replay, wrong/non-running rejection, heartbeat/progress retention,
  partial-result failure, exception propagation, and session closure.
- Schedule tests assert task registration, weekday 21:30 Shanghai defaults,
  configured values, stable kwargs, and disabled behavior.
- Final gate: focused and full pytest, full Vitest, TypeScript, touched-file
  Ruff, Alembic head/upgrade/downgrade, locale JSON, Trellis validation,
  PostgreSQL migration smoke, live 3000/8000 health, and `git diff --check`.
- Strict read-only acceptance scripts and runbooks must use bounded TaskRun SQL
  inside `BEGIN READ ONLY`; tests must reject TaskRun GET endpoints as
  zero-mutation probes.

### 7. Wrong vs Correct

#### Wrong

```python
decision_date = session.query(func.max(DailyBar.trade_date)).scalar()
evaluate_all_pending_outcomes(session)
generate_research_shortlist(ResearchShortlistGenerateInput(), session=session)
```

This trusts partial/intraday rows, scans unbounded historical work, and allows
publication to choose a different date from outcome evaluation.

#### Correct

```python
watermark = resolve_completed_daily_bar_watermark(session=session)
if watermark["status"] != "ready":
    return deferred_result(watermark)

completed_through = date.fromisoformat(watermark["verified_completed_through"])
evaluate_due_research_shortlist_outcomes(
    session=session,
    market="CN",
    profile_id="balanced_research",
    verified_completed_through=completed_through,
    evaluation_task_run_id=task_run_id,
    run_limit=25,
)
generate_research_shortlist(
    ResearchShortlistGenerateInput(
        verified_decision_date=completed_through,
        generation_task_run_id=task_run_id,
    ),
    session=session,
)
```

One local, completed-market watermark controls both bounded phases while the
existing publication gate and immutable domain identities remain authoritative.

For a strict zero-mutation TaskRun audit, the analogous boundary is:

#### Wrong

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/task-runs/latest?task_name=research.run_daily_research_loop"
```

This route can call stale-run expiration before returning the row.

#### Correct

```sql
BEGIN READ ONLY;
SELECT id, status, started_at, finished_at, result_json
FROM task_runs
WHERE task_name = 'research.run_daily_research_loop'
ORDER BY started_at DESC
LIMIT 10;
COMMIT;
```
