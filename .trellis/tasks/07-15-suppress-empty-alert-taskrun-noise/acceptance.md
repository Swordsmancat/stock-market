# Acceptance: Suppress empty alert TaskRun noise

Date: 2026-07-15

## Automated gates

- Final focused worker, service, schedule, and dispatcher suite: `60 passed`.
- Ruff: passed.
- Isolated mypy for both changed production modules: passed.
- Trellis context manifests: valid.
- Git diff check: passed.
- Celery active and reserved queues were empty before the Worker restart.

## Live queued acceptance

- Worker-only restart: PID `44072` replaced by PID `37764`.
- Beat remained PID `26696`; listeners on ports `3000` and `8000` were
  unchanged.
- Queued Celery task ID: `0de5758a-4e53-469f-bd28-7e0906579990`.
- Result: `skipped/no_alert_rules`, `item_count=0`, `triggered_count=0`, empty
  `items`.
- Read-only database result after the queued task: `173` alert TaskRuns, latest
  ID `e5714aa7-ce43-41e2-979f-ec23f04bf349` at
  `2026-07-15 03:00:00.006343+00`, zero AlertTrigger rows.

## Real Beat tick

After the `11:15` local schedule tick, the alert TaskRun count and latest
identity/timestamp remained unchanged and AlertTrigger count remained zero.
The Worker answered `pong`. Historical TaskRuns were not deleted or rewritten.

## Residual boundary

The accepted two-read race remains bounded: a concurrently added rule can wait
one 15-minute interval, while a concurrently removed rule can leave one
succeeded skipped TaskRun. Supplied TaskRuns and failures remain persisted.
