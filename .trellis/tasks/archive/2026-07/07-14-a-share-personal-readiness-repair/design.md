# Repair personal A-share evidence readiness - design

## Boundary

This is a reliability and data-bootstrap task over existing services. The only
runtime code changes make the existing scheduled incremental request and its
Celery scheduling task forward the already-supported `cn_resilient` policy. No
domain schema or public API changes.

## Data flow

```text
06:30 universe sync (already complete)
        |
        v
50-stock resilient daily-bar canary
        |
        v
full daily-bar baseline -> local technical baseline
        |
        v
fundamental shards 0..4, strictly sequential
        |
        v
existing 95/90/80 gate -> existing daily research loop
```

## Code changes

- `apps/worker/celery_app.py`: add `daily_bar_policy="cn_resilient"` to the
  weekday incremental kwargs.
- `apps/worker/tasks/ingestion.py`: accept and forward that policy through the
  existing scheduled-backfill task, retaining `strict` as its compatibility
  default for callers that do not supply a policy.
- `tests/worker/test_celery_schedule.py`: assert the policy is frozen in the
  scheduled request.
- `tests/worker/test_tasks.py`: assert the scheduling task forwards the policy
  into `BackfillRequest`.
- `tests/services/test_instrument_universe.py`: prove a legacy exact-symbol CN
  stock with no exchange is updated in place by the authoritative sync.

The provider mapper and universe service already work and remain unchanged.

## Runtime contracts

- All live writes target the normal local `stock` database through existing
  FastAPI/Celery paths.
- The bootstrap date range is 2025-01-13 through 2026-07-13. The end date is
  fixed to the last completed date so intraday 2026-07-14 rows cannot enter the
  initial watermark.
- Daily canary and baseline use `cn_resilient`; technical indicators are local
  only; fundamental shards use their existing AkShare path.
- A new run is dispatched only when no `queued|running|cancel_requested`
  CN/AkShare backfill exists.
- Canary release requires 48/50 successes, at most two retry symbols, and
  evidence from BSE/SSE/SZSE.
- Long runs retain normal checkpoints, sanitized diagnostics, pacing, source
  statistics, cooperative cancellation, and TaskRun heartbeat.

## Data hygiene

The cleanup is intentionally one-off and narrow: delete only DailyBar rows for
the canonical CN stock 600519 where both provider and source are
`legacy_unknown`, after confirming the expected count is nine. Provider rows,
instruments, fundamentals, and TaskRuns are not deleted.

## Failure and rollback

- Code rollback removes one Beat kwarg; manual resilient runs remain available.
- If canary fails its gate, do not create the full baseline.
- If a long run shows provider-wide failure, request cooperative cancellation
  and preserve its checkpoint/retry set.
- If the cleanup precondition is not exactly nine rows, abort cleanup and
  investigate rather than broadening the predicate.
- Existing coverage thresholds and daily-loop behavior are never changed.
