# Technical design

## Boundaries

- `OfficialDisclosureMonitorState` stores CNINFO/watchlist operational state; `OfficialDisclosure` remains the authoritative metadata corpus and `OfficialDisclosureDocument` remains the immutable content-version boundary.
- `official_disclosure_operations` owns cursor calculation, per-symbol retry transitions, candidate selection, TaskRun enqueue dedupe, and freshness serialization.
- The worker owns Celery execution and scheduling glue. The API and web proxy only validate/forward operator intent.
- Evidence Center displays monitoring state and newly discovered counts but does not infer document meaning.

## Persistent contract

Create `official_disclosure_monitor_states`, unique on `(source, symbol)`, with:

- cursor: `cursor_published_at`, `cursor_source_document_id`
- lifecycle: `last_attempted_at`, `last_success_at`, `last_failure_at`, `status`
- recovery: `consecutive_failures`, `next_retry_at`, sanitized `last_error_code`/`last_error_message`
- observability: `last_new_disclosure_count`, optional `last_task_run_id`, timestamps

The cursor advances only after a successful metadata refresh and is selected by `(published_at, source_document_id)`. Failures never erase or rewind it.

## Incremental data flow

1. Beat invokes a lightweight scheduler task.
2. The scheduler calls the same enqueue service used by the operator endpoint with `mode=incremental`.
3. Enqueue expires stale TaskRuns, reuses any running watchlist disclosure TaskRun, otherwise dispatches one run.
4. For each eligible symbol, incremental mode skips an active retry-backoff state and chooses `max(today-lookback, cursor-date-overlap)` as the provider start date.
5. Metadata refresh upserts official identities. The service compares the durable cursor and post-refresh rows, records the new count, and advances the watermark.
6. Pending-document selection remains bounded and excludes any disclosure whose latest document has `extraction_status=extracted`.
7. The service commits per-symbol state transitions, returns partial diagnostics where applicable, and the worker completes the TaskRun.

## Retry and mutex semantics

- Retry delay is exponential from a configurable base, capped by a configurable maximum.
- Scheduled incremental mode honors `next_retry_at`; explicit batch mode bypasses it so an operator can verify recovery.
- The single existing task name is retained for execution, and both entry points use its running-TaskRun lookup. This makes the mutex cover scheduled and manual operations without a second lock system.
- A provider-wide failure is represented by per-symbol sanitized failures and a failed/partial TaskRun result; existing metadata/documents and successful symbol checkpoints remain intact.

## Freshness and review contract

- Freshness states are `fresh`, `stale`, `backoff`, and `never` using a configurable `last_success_at` SLA.
- Evidence status returns scheduler configuration, aggregate counts, and per-symbol cursor/retry/freshness fields.
- `last_new_disclosure_count` identifies material for human review; no summary or investment decision is generated automatically.

## Compatibility and rollout

- The migration is additive and existing evidence APIs retain their current fields.
- Existing explicit ingestion requests default to `mode=batch`; the new monitor endpoint uses `mode=incremental`.
- Beat defaults are bounded and configurable. Deployments must apply Alembic migration and restart API/worker/beat to load the new route, model, and schedule.
- Rollback removes only monitor state; the official metadata and extracted document corpus is unaffected.

