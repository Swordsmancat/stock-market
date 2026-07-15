# Suppress empty alert TaskRun noise

## Goal

Keep the 15-minute personal watchlist alert schedule ready for future rules
without filling recent TaskRun history when the persisted watchlist currently
contains no actionable alert rules.

## Requirements

- Only direct periodic deliveries with `task_run_id=None` are eligible for the
  lightweight preflight suppression.
- Before creating a periodic TaskRun, read the persisted active watchlist and
  determine whether at least one item has a supported non-null alert rule.
- If no actionable rule exists, return the existing bounded result
  `status=skipped`, `reason=no_alert_rules`, `item_count=0`,
  `triggered_count=0`, and `items=[]` without creating a TaskRun, fetching
  market data, or writing an AlertTrigger.
- A supplied `task_run_id` from API dispatch or retry always bypasses
  suppression and completes/fails that existing TaskRun through the current
  lifecycle, including an explicit skipped result when no rules exist.
- When actionable rules exist, TaskRun creation, evaluation, trigger dedupe,
  provider behavior, result shape, and exception propagation remain unchanged.
- If the best-effort preflight raises, roll back the session and continue into
  the existing TaskRun lifecycle so the repeated service error is recorded and
  re-raised rather than hidden.
- Preserve watchlist bootstrap/soft-removal semantics, the 15-minute schedule,
  notification UI, homepage, daily research loop, and five-day acceptance.
- Do not delete or rewrite historical TaskRuns.

## Acceptance Criteria

- [x] A regression test proves the current direct empty/no-rule delivery
      creates a TaskRun before the fix.
- [x] After the fix, the same delivery returns the exact skipped result with
      zero TaskRun and AlertTrigger rows.
- [x] A supplied empty-scope TaskRun is reused and finished succeeded with the
      skipped result rather than suppressed.
- [x] An actionable rule still creates one succeeded TaskRun and preserves
      trigger recording.
- [x] A preflight exception falls through to the normal lifecycle and remains
      observable as a failed TaskRun if evaluation repeats the error.
- [x] Focused worker/service/schedule tests, Ruff, isolated mypy, Trellis check,
      and diff checks pass.
- [x] Live queued acceptance returns skipped while the latest persisted alert
      TaskRun ID/count remains unchanged.
- [ ] Minimal code/spec/task files are committed and pushed, this task is
      archived, and the five-day acceptance is restored as current.

## Out of Scope

- Disabling alerts, changing their interval, or hiding failed/evaluated runs.
- Suppressing official-disclosure or other scheduled TaskRuns in this change.
- Retention/deletion of historical TaskRuns or changes to Task Runs UI filters.
