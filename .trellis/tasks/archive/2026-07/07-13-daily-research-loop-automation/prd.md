# Daily research loop automation

## Goal

Run the existing A-share research decision loop automatically after trustworthy
local market evidence is complete: mature due 5/20/60-session observations for
previous cohorts, then publish or reuse one immutable daily research shortlist.
The automation must be observable, retryable, idempotent, and strictly
research-only.

This task closes the operational loop. It does not broaden the product into a
backtester, strategy optimizer, portfolio manager, provider crawler, or trading
system.

## Background

- Persisted daily shortlist generation and outcome tracking are already
  implemented and share local database evidence.
- `generate_research_shortlist()` currently derives its decision date from the
  maximum stored stock bar. One partial or intraday row can therefore advance
  the date before full-market evidence is ready.
- The existing evidence coverage response preserves the 95/90/80 publication
  thresholds, but its daily-bar readiness is an 18-month freshness measure. It
  is not an exact-date completed-market watermark.
- Outcome evaluation already accepts an internal verified cutoff and optional
  TaskRun lineage, but no service selects every historical cohort that has
  genuinely become due.
- Generic TaskRun list/detail/retry pages already provide the required operator
  surface. A separate automation dashboard would duplicate them.
- Celery already uses `Asia/Shanghai`; weekday A-share evidence work runs at
  18:30 and 20:30.

## Requirements

### R1. Trusted completed daily-bar watermark

- Resolve the latest trustworthy local A-share stock date without making any
  provider or network call.
- Defer while any CN/AkShare evidence backfill is queued, running, or
  cancellation-pending so publication cannot race evidence replacement.
- A terminal backfill may provide the candidate date range only when it is a
  full-scope `baseline` or `incremental` run, includes `daily_bars`, has status
  `succeeded` or `partial`, and has a non-null finish time. Canary,
  fundamental-shard, retry-failed, failed, cancelled, and active runs cannot
  establish a market watermark.
- Within the eligible range, require completed exact-date bars for at least 95%
  of the current active CN stock universe and nonzero SSE, SZSE, and BSE
  representation. A bar is complete only when its ingestion timestamp is at or
  after 16:00 Asia/Shanghai on its trade date, or on a later Shanghai date.
- Reject future dates and the current Shanghai date before 16:00. Weekend and
  holiday handling comes from stored trade dates rather than a fabricated
  calendar.
- Keep the existing publication readiness thresholds unchanged: 95% daily
  bars, 90% critical technical indicators, and 80% complete fundamentals.
  The shortlist service remains the authority for the full publication gate.

### R2. Safe shortlist publication

- The scheduled caller must pass the verified decision date through an
  internal-only service field. Browser/FastAPI callers cannot assert a trusted
  date or TaskRun lineage.
- A partial newer bar inserted after watermark resolution must not move the
  automated decision date.
- Preserve the existing generation key, serialized generation lock, unique
  constraint, point-in-time screening, deterministic ranking, LLM validation,
  and immutable first publication.
- Persist nullable `generation_task_run_id` on a newly committed shortlist run
  and expose it in existing latest/detail payloads. Reuse must not overwrite the
  original publisher; the current retry TaskRun records the reused run in its
  own result.

### R3. Bounded historical outcome maturation

- Select committed CN stock cohorts for the configured profile when at least
  one missing candidate horizon has enough completed forward bars through the
  verified cutoff.
- Give candidate-terminal work priority over optional benchmark enrichment.
  Revisit a pending benchmark only when the canonical CSI 300 instrument and
  exact completed entry/maturity bars exist, so absent benchmark evidence does
  not create a permanent daily no-op queue.
- Process a deterministic oldest-due-first batch, default 25 runs and hard
  maximum 100. Inactive or delisted candidates remain in cohort accounting and
  do not block other due candidates.
- Call the existing per-run evaluator with the same verified cutoff and current
  TaskRun ID. Do not duplicate horizon calculations or write outcome rows from
  the orchestrator.
- Catch, roll back, sanitize, and bound per-cohort failures, continue the
  remaining due cohorts, and still attempt current shortlist publication.
- Expose `evaluation_task_run_id` on terminal outcome payloads; derived pending
  horizons have null lineage. Existing terminal observations remain immutable.

### R4. One daily orchestration unit

- Add one service-layer daily loop and one Celery task named
  `research.run_daily_research_loop`.
- After a ready watermark, mature due historical cohorts and then generate or
  reuse the current shortlist. The two phases are independently reportable.
- Active backfill or missing/unready daily watermark is an expected deferred
  result and a succeeded TaskRun. Publication readiness failure after outcomes
  were matured is also an honest succeeded result with deferred generation.
- Any unexpected system failure, or one or more isolated cohort failures after
  the remaining work is attempted, produces a failed TaskRun and re-raised
  Celery error. Preserve a bounded partial result before failing.
- Update TaskRun heartbeat/progress at watermark, outcome, publication, and
  completion boundaries. Long healthy work must not be declared stale by the
  API or the read-only health script.

### R5. Scheduling and retry

- Schedule the task on weekdays at 21:30 Asia/Shanghai by default, after the
  existing evidence windows. The schedule is configurable and enabled by
  default.
- Fixed clock time is not evidence authority; every invocation must repeat the
  active-backfill and watermark gates.
- Register the task in generic TaskRun dispatch so the existing retry endpoint
  creates a new TaskRun with `retry_of` and converges on the same domain state.
- Do not use Celery automatic retries and do not start an AkShare backfill from
  the research task.

### R6. Existing operational surfaces

- Reuse `/task-runs` recent/latest/detail/retry and existing AI Research
  shortlist/outcome/coverage panels. Do not add a task-specific page or place
  research-loop state inside the evidence backfill panel.
- Store structured, bounded TaskRun results containing watermark provenance,
  due/processed/failed cohort counts, shortlist run/date/item count, progress,
  and research-only safety flags.
- Do not persist credentials, provider payloads, LLM prompts, raw upstream
  responses, or unbounded exception text.

### R7. Safety and product focus

- Preserve `research_signal_only=true`, deterministic membership/ranking, and
  the rule that outcomes never change later shortlist weights or membership.
- Emit no buy/sell/hold action, target price, position size, portfolio weight,
  order intent, broker route, or automated execution.

## Acceptance Criteria

- [x] A newer exact date held by fewer than 95% of active stocks cannot become
      the watermark; exactly 95% with SSE/SZSE/BSE representation can.
- [x] Completion boundaries cover pre/post 16:00 Shanghai, later-day backfills,
      naive SQLite UTC timestamps, future dates, and current-day gating.
- [x] Only finished full-scope baseline/incremental daily-bar runs can provide
      watermark provenance; active or partial evidence replacement defers the
      loop without provider access.
- [x] A ready run passes the exact verified date into generation, publishes one
      idempotent shortlist, and records immutable generation TaskRun lineage.
- [x] Existing 95/90/80 coverage thresholds still gate publication, and a
      readiness failure creates no partial shortlist row.
- [x] At least two historical cohorts can mature in one bounded run; candidate
      work is prioritized, missing CSI 300 evidence does not create daily
      no-op processing, and inactive candidates remain represented.
- [x] New terminal outcomes store and serialize evaluation TaskRun lineage;
      repeated, concurrent, scheduled, and retry execution does not duplicate
      or revise terminal domain rows.
- [x] Expected deferred states finish TaskRun successfully with structured
      reasons; unexpected or per-cohort failures preserve partial diagnostics,
      fail TaskRun, re-raise, and close the worker session.
- [x] Generic TaskRun retry dispatches the new task with `retry_of`; direct Beat
      invocation creates its own TaskRun and both paths update heartbeat.
- [x] Celery Beat uses the configurable weekday 21:30 Shanghai schedule, and
      healthy long-running TaskRuns are not falsely reported stale.
- [x] Migration `0022` upgrades and downgrades the nullable shortlist TaskRun
      foreign key and index without changing existing shortlist rows.
- [x] Existing TaskRun and AI Research UI tests remain green without a new
      frontend surface; normal ports 3000/8000 remain healthy.
- [x] Focused and full backend tests, Ruff, Alembic checks, Trellis validation,
      and `git diff --check` pass with no live provider/network dependency.

## Out of Scope

- Historical shortlist reconstruction for missed days.
- Backtesting, strategy/threshold optimization, self-learning weights, or alpha
  claims.
- Portfolio construction, transaction costs, slippage, orders, brokers, or
  trading execution.
- New provider integrations, automatic evidence repair, parallel AkShare work,
  OCR, embeddings, or vector search.
- A dedicated automation dashboard, scheduler controls, or new public trusted
  watermark API.
