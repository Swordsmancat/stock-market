# Acceptance report

## Outcome

The repeated empty-watchlist report failure is fixed. A persisted default
watchlist with historical inactive items is now authoritative, resolves to an
empty scope, and completes the nightly worker TaskRun as a bounded successful
skip without calling market, provider, or AI analysis.

## Root cause

The persisted read correctly returned no active entries, but
`_default_watchlist_value()` treated that successful empty result like a
database failure and restored `settings.daily_report_watchlist`. The two
deactivated placeholders were then analyzed, and the indicator lookup required
an `Instrument` row that did not exist.

The issue occurred on both 2026-07-13 and 2026-07-14. Beat did not pass a stale
watchlist argument; the fallback happened inside the worker. The 2026-07-14
start delay was caused by a long single-worker evidence backfill, not this bug,
so schedule/concurrency was left unchanged.

## Automated verification

- Regression test before fix: failed because `refresh_stock_analysis` was
  called for the configured fallback symbol.
- Regression test after fix: 1 passed.
- Empty-list and explicit-empty/reused-TaskRun regressions: 2 passed.
- Full `tests/worker/test_tasks.py`: 24 passed.
- Watchlist service tests: 3 passed.
- Combined worker, Beat schedule, and watchlist service gate: 39 passed.
- Ruff on both changed Python files: passed.
- Isolated mypy with skipped dependency traversal on the changed worker file:
  passed.
- The repository's normal transitive mypy invocation remains blocked by 164
  pre-existing errors across 36 imported files, including missing third-party
  stubs; no reported error points to this change.

## Live verification

- Direct real-database call created TaskRun
  `0652d6ad-ab6d-40c1-a2b9-b48680a33396` with `status=succeeded` and result
  `skipped/empty_watchlist/0`.
- The idle Celery worker was restarted to load the fix; Beat, Web, API,
  PostgreSQL, and Redis were not restarted.
- The replacement worker returned `pong` as node `stock-local`.
- A queued Celery call created TaskRun
  `2bbc59d4-1b4f-425c-9d34-ae3e9bc4361f` with the same succeeded skipped
  result, proving the deployed worker loaded the fix.
- The persisted active watchlist count remained zero, no TaskRun remained
  active, Web returned HTTP 200, and API health returned `ok`.

No provider or model request was made by either empty-list acceptance call.
