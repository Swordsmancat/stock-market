# Five-day personal research acceptance execution plan

## 1. Establish the baseline

- Confirm the normal Web/API/PostgreSQL/Redis/Worker/Beat stack without
  restarting healthy services.
- Read the latest daily-loop TaskRun with a read-only SQL transaction.
- Read the latest shortlist and outcome tracking through non-mutating GETs.
- Write sanitized `artifacts/preflight.json` and initialize
  `artifacts/progress.json`; do not count the baseline trusted watermark.
- Validate JSON structure and scan the task directory for credential patterns.

## 2. Start the monitor

- Validate and start this Trellis task after the planning artifacts and context
  manifests are complete.
- Create one task-attached weekday heartbeat for 22:15, 22:45, 23:15, and
  23:45 Asia/Shanghai so a late loop receives bounded same-night rechecks.
- Persist its automation ID in the progress ledger so later wakes update or
  disable the same automation instead of creating duplicates.
- Verify the stored schedule and prompt after creation.

Rollback point: disable the heartbeat; no application/domain state changes
need reversal.

## 3. Observe each sampled trading date

- Run service, database, Worker, Beat, and read-only daily-loop checks.
- Query a bounded 31-day history of scheduled TaskRuns and select at most one
  oldest unreserved trusted watermark newer than the baseline.
- If a loop is active or no new watermark exists, record pending/skip state;
  increment no-progress at most once per Shanghai weekday window.
- For a new watermark, atomically create
  `artifacts/reservations/YYYY-MM-DD.json` with exclusive-create semantics.
  Never call the assistant if this operation reports that the marker exists.
- Update the day artifact/progress projection after reservation. Missing
  shortlist or rank one is a counted failure with
  `not_attempted_precondition`.
- Otherwise make one assistant request for the rank-one candidate with no
  retry, then store only the permitted response subset.
- Validate citation IDs, coverage gates, shortlist identity, cohort uniqueness,
  and safety flags; classify the date without replacing a failed sample.
- Never invoke generate/evaluate/retry/backfill/watchlist/portfolio/order APIs.

## 4. Handle evidence-backed blockers

- Preserve the first occurrence as evidence; do not change code for isolated
  provider, timing, or model incidents.
- On a repeated reproducible product blocker, load the relevant Trellis specs,
  add focused regression coverage, implement the smallest fix, and run focused
  plus proportional full validation.
- Commit and push the fix without staging unrelated user changes, then continue
  the same five-date sample without replacing failed dates.

## 5. Complete or stop blocked

- Confirm exactly five unique reservation/day artifacts and at most one
  assistant attempt per date.
- Immediately persist `finalizing`; all future wakes bypass the assistant.
- Aggregate pass/degraded/fail assertions and repeated issues into
  `acceptance.md`; distinguish expected 20/60-session pending outcomes.
- If `2026-08-05T23:59:59+08:00` or the seventh distinct no-progress weekday
  window arrives first, write the same report with `blocked` status.
- Run JSON validation, secret scan, Trellis validation/check, and
  `git diff --check` scoped to task-owned files plus any authorized fix.
- Attempt commit/push, Trellis finish/archive, and journal recording. Disable
  the heartbeat in a `finally` path for complete and blocked outcomes; record a
  delivery failure without re-enabling the paid-call branch.

## Validation commands

```powershell
python ./.trellis/scripts/task.py validate 07-15-five-day-personal-research-acceptance
python scripts/dev_health_check.py
python scripts/task_run_health.py --stale-minutes 30 --recent-limit 20
git diff --check -- .trellis/tasks/07-15-five-day-personal-research-acceptance
```

Application tests are required only when application code changes. Evidence-
only wakes run task validation, JSON parsing, redaction checks, and bounded
runtime probes.
