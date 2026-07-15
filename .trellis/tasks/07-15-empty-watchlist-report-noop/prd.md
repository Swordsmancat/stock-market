# Treat empty watchlist report as no-op

## Goal

Make the scheduled personal watchlist analysis complete successfully and
explicitly skip work when the persisted default watchlist intentionally has no
active items, instead of resurrecting deactivated configuration placeholders
and failing the TaskRun.

## Requirements

- The persisted watchlist is authoritative once it contains historical items.
  Zero active items after soft removal is a valid personal-use state.
- Initial bootstrap behavior remains unchanged: when no watchlist items have
  ever existed, the watchlist service may seed `DAILY_REPORT_WATCHLIST`.
- Database read failures retain the existing fallback to
  `settings.daily_report_watchlist`; an intentional empty result must not use
  that error fallback.
- A scheduled or direct watchlist-analysis task with an empty resolved list
  creates/reuses its TaskRun, makes no market/provider/AI analysis call, and
  finishes the TaskRun as succeeded.
- The bounded result for an empty list is
  `status=skipped`, `reason=empty_watchlist`, `item_count=0`, and `items=[]`.
- Explicit non-empty watchlists and non-empty persisted watchlists keep their
  current report generation and TaskRun lifecycle behavior.
- Do not change Beat timing, daily research scheduling, homepage behavior,
  watchlist rows, provider configuration, or the active five-day acceptance
  thresholds/sample rules.

## Acceptance Criteria

- [x] A regression test reproduces the current bug with historical inactive
      watchlist items and fails before the implementation change.
- [x] The same test passes after the fix and proves `refresh_stock_analysis`
      was not called.
- [x] The empty-list TaskRun succeeds with the explicit bounded skipped result.
- [x] Existing worker watchlist-report and watchlist service tests pass.
- [x] Focused lint/type checks, Trellis validation/check, and diff checks pass.
- [ ] Only task-owned files and the minimal worker/test/spec changes are
      committed and pushed; unrelated working-tree changes remain untouched.
- [ ] The original five-day acceptance task is restored as the active Trellis
      task after this fix is archived.

## Out of Scope

- Removing the watchlist-report feature or changing its schedule.
- Automatically adding symbols to an intentionally empty watchlist.
- Per-symbol partial-failure redesign, provider retries, or report UI changes.
