# Alert TaskRun noise diagnosis

## Runtime evidence

Within the last seven days, `alerts.evaluate_watchlist_alerts` produced 172
succeeded TaskRuns with an average duration of 9 ms. In the latest 50 TaskRuns,
35 entries (70%) were this task with `result.status=skipped`; another nine were
unrelated disclosure no-data runs. The latest alert result was
`skipped/no_alert_rules`, and the persisted watchlist has zero active items and
zero AlertTrigger rows.

## Call path

Celery Beat delivers `alerts.evaluate_watchlist_alerts` every 15 minutes without
a `task_run_id`. The worker immediately calls `start_task_run()` and only then
calls `evaluate_all_watchlist_alerts()`. The service loads active watchlist
items, filters for supported rules, and returns a bounded skip before any market
lookup when no actionable rule exists. The no-op is therefore cheap but its
persisted TaskRun hides more meaningful work in recent-history views.

The notification bell and Alerts page read `AlertTrigger` records; they do not
consume skipped TaskRuns. Generic API dispatch/retry creates a TaskRun before
delivery and supplies its ID, so that path must remain fully observable.

## Ranked hypotheses

1. TaskRun creation precedes the existing no-rule guard. Moving only a
   best-effort actionable-rule preflight ahead of direct Beat TaskRun creation
   will remove the noise without disabling automatic recovery.
2. Most skipped rows came from manual/API dispatch. The exact 15-minute cadence
   and Beat configuration predict they are direct periodic deliveries.
3. Skipped TaskRuns are required by the notification UI. Source tracing predicts
   the UI depends on `AlertTrigger` instead.
4. Preflight suppression could hide genuine database errors. Bypassing
   suppression after any preflight exception and repeating the read inside the
   normal lifecycle keeps those failures visible.

## Feedback loop

Use the existing SQLite worker seam. Invoke the alert task without a supplied
TaskRun in a session with no actionable rules and assert the service skip result
plus zero `TaskRun` and `AlertTrigger` rows. This test fails on current code
because one succeeded TaskRun is persisted. Companion tests cover supplied
TaskRun reuse, actionable rules, and preflight-error fallback.

## Resolution and live acceptance

The worker now performs the actionable-rule read only for direct deliveries
without a supplied `task_run_id`. A successful no-rule preflight returns the
existing bounded skip payload before TaskRun creation. Supplied TaskRuns,
actionable evaluations, and repeated preflight errors retain the original
observable lifecycle.

On 2026-07-15, the production Worker was restarted from PID `44072` to PID
`37764` while Beat PID `26696`, the web listener on port `3000`, and the API
listener on port `8000` remained running. Celery task
`0de5758a-4e53-469f-bd28-7e0906579990` returned the exact
`skipped/no_alert_rules` payload. A read-only database transaction then showed
`173` alert TaskRuns, latest ID `e5714aa7-ce43-41e2-979f-ec23f04bf349` at
`2026-07-15 03:00:00.006343+00`, and zero AlertTrigger rows.

After the real `11:15` local Beat tick, the same read-only queries returned the
same count, latest ID/timestamp, and trigger count. The restarted worker also
answered `pong`. This proves both explicit queued invocation and the unchanged
15-minute schedule suppress only the known no-work persistence noise.
