# Empty watchlist report diagnosis

## Runtime symptom

Strict read-only SQL found two consecutive scheduled failures:

- 2026-07-13: `reports.refresh_daily_watchlist_analysis` failed with
  `No row was found when one was required`.
- 2026-07-14: the same task failed with the same message.

The persisted state contains one default watchlist, two historical items
(`TEST:US` and `CN_SHANGHAI_COMPOSITE:CN`), and zero active items. Both items
were intentionally soft-deactivated during the approved personal-workflow
cleanup.

## Call path and leading hypothesis

`refresh_daily_watchlist_analysis()` resolves a missing task argument through
`_default_watchlist_value()`. That helper calls
`get_active_watchlist_entries()`, which correctly returns an empty list for a
watchlist with historical inactive items. The helper then treats the empty list
as missing database configuration and returns `settings.daily_report_watchlist`
instead. The scheduled TaskRun consequently records the two deactivated
placeholder identities and sends them through `refresh_stock_analysis()`.

Ranked falsifiable hypotheses:

1. Empty persisted entries are incorrectly replaced by settings fallback. If
   empty entries are preserved, the task will make zero analysis calls and
   finish successfully.
2. Beat passes the stale list explicitly. If true, changing default resolution
   will not affect scheduled input.
3. The worker is executing stale code/configuration. If true, a direct focused
   test will pass while the live worker still records the old list.
4. The provider fails independently of watchlist resolution. If true, an empty
   task will still reach the provider and fail after the fallback is removed.

## Deterministic feedback loop

At the existing worker test seam:

1. Create the SQLite test session.
2. Add one watchlist item and soft-remove it, leaving historical state but no
   active entries.
3. Replace `refresh_stock_analysis` with a spy that fails if called.
4. Invoke `refresh_daily_watchlist_analysis()` without a watchlist argument.
5. Assert a succeeded TaskRun and the exact bounded skipped result.

This reproduces the production state without PostgreSQL, Redis, Celery, or a
real provider and directly distinguishes hypothesis 1 from the alternatives.

## Conclusion

Hypothesis 1 was confirmed. The pre-fix regression called analysis for `AAPL`
after the persisted active list returned empty. Beat's kwargs contain no
watchlist, falsifying hypothesis 2; the same failure reproduced in the current
test process, falsifying stale-worker code as the cause; and the fail-if-called
probe showed provider work was downstream of the incorrect fallback rather
than an independent trigger.

After the fix, focused tests, a direct PostgreSQL-backed invocation, and a task
queued through the restarted Celery worker all returned the exact bounded
`skipped/empty_watchlist` result with no analysis call.
