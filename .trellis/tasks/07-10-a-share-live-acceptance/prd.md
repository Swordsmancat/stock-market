# A-share Live Acceptance

## Goal

Prove the complete AkShare-backed A-share research pipeline in an isolated, reproducible runtime, classify real-provider findings, and preserve sanitized evidence for operators without touching the normal `stock` database.

## Requirements

- Add an acceptance-only Compose stack/project using PostgreSQL database `stock_acceptance`, isolated Redis, dedicated ports/volumes, `APP_ENV=acceptance`, API, worker, beat, and Web.
- Add a mutating acceptance runner with explicit `--real-network` and `--confirm-acceptance-writes` guards; abort unless the database name is exactly `stock_acceptance`.
- Run the existing read-only AkShare preflight before migrations, task dispatch, or other acceptance writes.
- Record commit, versions, migration head, timezone, sanitized runtime metadata, commands, timings, TaskRun IDs, exchange counts, coverage, diagnostics, and finding classifications.
- Exercise universe sync, safe reconciliation, corporate-action cursor/idempotency, a 50-symbol three-exchange evidence canary, resume/retry behavior when applicable, all discovery profiles, deterministic replay/fallback, and UI/TaskRun routes.
- Only proceed to a full 18-month baseline after the provider preflight and bounded canary are usable; retain checkpoints and stop on provider-wide schema/rate failures.
- Keep secrets, connection credentials, cookies, authorization headers, raw upstream payloads, and raw exceptions out of committed evidence.
- Do not lower coverage thresholds, silently switch providers, modify the normal `stock` database, or introduce trading behavior to make acceptance pass.

## Acceptance Criteria

- [x] The runner rejects missing guards, non-acceptance database names, and unsafe artifact content in focused tests.
- [x] The isolated stack configuration uses dedicated database/Redis state and ports and can be started/stopped with documented commands.
- [x] Read-only AkShare preflight is recorded before every mutating phase and write execution aborts on preflight failure.
- [x] The real universe API/worker path records a terminal TaskRun and non-empty SSE/SZSE/BSE distribution without modifying the normal database.
- [x] A deterministic 50-symbol canary records bars/fundamentals/indicators, classified gaps/retries, coverage, and TaskRun lineage.
- [x] Corporate-action batches and replay evidence show deterministic cursor/idempotency behavior, or a classified provider limitation blocks the slice.
- [x] All discovery profiles are replayed over unchanged stored evidence with full stored scope, stable ranking, timing, coverage, and deterministic LLM fallback.
- [x] AI Research, Evidence Center, and TaskRun routes are checked at desktop/mobile sizes with sanitized console/network observations.
- [x] A full baseline is completed or left in an explicit resumable/partial state with checkpoint, retry set, threshold evaluation, and an honest blocking classification.
- [x] A sanitized Markdown/JSON report and operator runbook document setup, abort conditions, resume/retry/cancel, schedules, cleanup, and retained evidence.
- [x] Focused/full backend and Web gates, TypeScript, touched-file Ruff, migration head, locale parse, Trellis validation, and `git diff --check` pass for any code changes.

## Out of Scope

- Paid-provider procurement, Tushare credentials, multi-provider reconciliation, external corpus ingestion, formal provider SLA claims, broker integration, orders, or automated trading.
- Destructive cleanup of successful evidence outside the isolated acceptance project.
