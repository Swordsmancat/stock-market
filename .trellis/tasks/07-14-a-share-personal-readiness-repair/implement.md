# Repair personal A-share evidence readiness - implementation plan

## 1. Lock existing repair behavior

- Add the legacy null-exchange universe reconciliation regression.
- Add `cn_resilient` to the weekday incremental Beat kwargs and update the
  schedule regression.
- Forward the policy through the existing scheduling task while preserving its
  `strict` default, and add a worker regression for that boundary.
- Run the focused provider, universe, schedule, and backfill tests.

## 2. Clean proven local test evidence

- Query and record the exact nine `600519` `legacy_unknown` DailyBar rows.
- Delete them in one transaction only when the expected count matches.
- Re-query source distribution and keep all provider rows intact.

## 3. Bootstrap daily evidence

- Assert no active backfill, then dispatch a 50-symbol daily-only resilient
  canary for 2025-01-13 through 2026-07-13.
- Poll checkpoints and release only at 48/50 success, retry <=2, and all three
  exchanges represented.
- Assert no active backfill, then dispatch the full daily-only resilient
  baseline and monitor to a terminal state.
- Verify exact-date and 18-month daily coverage pass 95%.

## 4. Complete local and fundamental evidence

- Dispatch one technical-indicators-only baseline and verify 90% readiness.
- Dispatch fundamental shards 0, 1, 2, 3, and 4 sequentially, checking the
  active-run guard before every shard and verifying final 80% readiness.

## 5. End-to-end acceptance

- Run the existing daily research Celery task and verify trusted watermark,
  shortlist create/reuse, TaskRun lineage, and research-only safety.
- Verify ports 3000/8000 and Celery registration remain healthy.
- Run touched Ruff, focused and full pytest, frontend tests/TypeScript if any
  shared response changed, Trellis validation, and `git diff --check`.
- Update the task verification record, commit, push, archive, and journal.

## Rollback points

- Schedule change: revert only the incremental policy kwarg.
- Data cleanup: stop if the exact precondition is not met; no broad delete.
- Live runs: cooperative cancel at the next checkpoint and preserve progress.

## Verification Record - 2026-07-14

- Removed exactly nine `600519` rows where both provider and source were
  `legacy_unknown`; the 361 provider-attributed AkShare rows remained intact.
- Canary `f52b37fd-04aa-44e4-8e02-423f57840e87` attempted 50 symbols and
  succeeded for 49, with one retry and usable BSE/SSE/SZSE evidence.
- Daily baseline `97c34568-50c2-4a31-bfe1-4db30cffb407` attempted all 5,530
  symbols and succeeded for 5,526. Final ready coverage is 5,508/5,530
  (99.6022%), including BSE 315, SSE 2,305, and SZSE 2,888.
- Technical baseline `3d328b35-5252-467f-890b-19690f158f8a` succeeded for
  5,516 symbols, with 10 explicit insufficient-history and four no-data
  outcomes. Ready coverage is 99.7468%.
- Fundamental shards 0 through 4 each succeeded for 1,106/1,106 symbols,
  sequentially. Ready coverage is 5,530/5,530 (100%).
- Daily research TaskRun `bb23ac63-fba9-4d43-bce4-0928fe59f6c2` resolved a
  trusted 2026-07-13 watermark and created shortlist
  `c0f33ccf-4ccf-44e7-88e0-e74d555d327a`. TaskRun
  `9bca494f-c27e-42d5-9640-4d81d044d0f3` reused the same shortlist and kept
  the original generation lineage unchanged.
- Final backend gate: 786 passed. Touched Ruff, isolated changed-file mypy,
  Trellis validation, and `git diff --check` passed. Repository-transitive
  mypy still reports 164 pre-existing errors across 36 unrelated/imported
  files; no new error points at the changed lines.
- Normal ports 3000/8000 finished healthy. One simultaneous port timeout during
  shard 4 recovered without affecting the backfill heartbeat and did not recur
  under a 20-second double-confirmation check.
- Final worker/Beat reload uses PIDs 33068/122396. Worker ping and task
  registration pass, Redis queue length is zero, the loaded 18:30 kwargs use
  `cn_resilient`, and the scheduling task compatibility default is `strict`.
- No UI, provider, schema, threshold, portfolio, optimizer, permission, or
  trading behavior was added.
