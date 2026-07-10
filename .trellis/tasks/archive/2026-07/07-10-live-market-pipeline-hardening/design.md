# Live Full-Market Pipeline Acceptance and Production Hardening Design

## 1. Architecture Summary

This task extends the existing modular-monolith boundaries rather than importing an external crawler runtime:

```text
AI Research UI
  -> Next.js no-store proxy routes
  -> FastAPI ingestion/coverage endpoints
  -> backfill orchestration service
  -> TaskRun + ResearchEvidenceBackfill state
  -> Celery bounded-batch worker
  -> AkShare provider / local indicator calculation
  -> DailyBar / FundamentalSnapshot / TechnicalIndicator
  -> coverage projection
  -> deterministic stock discovery
```

The first production provider is AkShare. Provider identity remains an explicit input and output, but failures never select another provider automatically.

## 2. Parent/Child Task Map

The current task is the integration parent and owns the source requirements, thresholds, and final live acceptance. Implementation should be split after planning approval:

1. `a-share-resumable-evidence-backfill`
   - Database state, TaskRun heartbeat/cancellation, provider diagnostics, backfill service, worker, API, schedules, coverage projection, and backend tests.
2. `a-share-backfill-operations-ui`
   - Next.js proxies, AI Research coverage/progress/actions, localization, and frontend tests.
3. `a-share-live-acceptance`
   - Isolated acceptance compose/runtime, read-only preflight, 50-100 symbol canary, real corporate-action batches, full-market execution, browser evidence, sanitized acceptance report, and runbook.

Child 2 depends on the API contract from child 1. Child 3 depends on children 1 and 2. The parent is archived only after cross-child acceptance criteria pass.

## 3. Persistence Design

### 3.1 ResearchEvidenceBackfill

Add a dedicated root-run model and Alembic revision. It stores durable orchestration state without placing thousands of success rows inside `TaskRun.result_json`:

- `id`: UUID primary key.
- `task_run_id`: nullable unique link to the authoritative TaskRun attempt.
- `parent_run_id`: nullable link for resume/retry lineage.
- `market`, `provider`, `run_kind`: `baseline`, `incremental`, `fundamental_shard`, `canary`, or `retry_failed`.
- `status`: `queued`, `running`, `partial`, `succeeded`, `failed`, `cancel_requested`, or `cancelled`.
- `universe_sync_id` and `universe_as_of`: freeze the accepted universe revision for deterministic ordering.
- `evidence_kinds`: ordered JSON list containing `daily_bars`, `fundamentals`, and/or `technical_indicators`.
- `scope_symbols_json`: the frozen normalized symbol order for this run, so later universe changes cannot reinterpret the cursor.
- `start_date`, `end_date`, `batch_size`, and optional `cohort_size` / `shard_index` / `shard_count`.
- `phase`, `cursor`, `phase_total`, and `processed_count`.
- `counters_json`: per-kind attempted/succeeded/no-data/failed/insufficient counts and exchange breakdown.
- `retry_json`: normalized per-kind symbol lists needed for deterministic retry.
- `diagnostics_json`: bounded sanitized aggregate diagnostics; no raw upstream payloads or secrets.
- `cancel_requested_at`, `heartbeat_at`, `created_at`, `updated_at`, and `finished_at`.

Successful evidence remains in the existing `DailyBar`, `FundamentalSnapshot`, and `TechnicalIndicator` tables. Current coverage is projected from those source-of-truth tables; the backfill row owns only orchestration/checkpoint state.

### 3.2 TaskRun heartbeat

Add nullable `TaskRun.heartbeat_at`. `start_task_run()` initializes it, progress updates refresh it, and stale expiration uses `heartbeat_at` with `started_at` fallback. This prevents a healthy multi-hour run from being failed merely because its original start time is older than 30 minutes.

Cancellation is cooperative. The backfill row moves to `cancel_requested`; the worker checks between symbols/batches, commits completed work, records the current cursor, marks the run `cancelled`, and completes the TaskRun with an explicit cancelled result. No process kill or rollback of already accepted evidence is attempted.

## 4. Deterministic Work Selection

- Baseline and incremental runs freeze the active CN stock universe at creation using the latest accepted AkShare universe sync metadata.
- Symbol ordering is `(exchange, symbol)` with normalized exchange values `SSE`, `SZSE`, and `BSE`.
- A canary cohort is deterministic and stratified across all three exchanges, with 50-100 total symbols and stable sampling from sorted exchange lists.
- Fundamental shards use `stable_symbol_ordinal % 5 == shard_index`, so each symbol belongs to exactly one daily shard and replay produces the same membership.
- Retry runs use normalized sorted symbol lists from the parent run's `retry_json`; they do not rescan unrelated successful symbols.
- A universe change after run creation does not reorder the current run. New or reactivated instruments enter the next run.

## 5. Execution Phases

The worker processes explicit phases so local calculation never repeats successful network work unnecessarily:

1. `daily_bars`
   - AkShare only, 18-month baseline or 10-calendar-day incremental window.
   - Reuse the existing single-symbol persistence path.
   - Commit per symbol as today; advance the durable cursor only after the batch is classified.
2. `fundamentals`
   - Fetch the latest AkShare financial analysis snapshot per symbol.
   - Preserve `no_data`, `provider_error`, and stored result distinctions.
3. `technical_indicators`
   - Read stored bars only and calculate locally.
   - A missing/insufficient bar window is classified, not fetched again implicitly.

Default batch size is 25 and the API bounds it to `1..100`. Provider calls are sequential by default with configurable pacing and bounded exponential retry for transient failures. No-data is not automatically retried in the same batch. Provider exception type/code is sanitized and aggregated; full response bodies are never persisted.

After each batch the service atomically updates the run cursor, counters, retry set, heartbeat, and TaskRun progress. Replaying a partially completed batch is safe because existing bar, fundamental, and indicator persistence is idempotent by domain identity.

## 6. Provider Error Boundary

AkShare daily-bar code must distinguish an actual empty dataframe from import/network/schema failure. Catch-all conversion of provider exceptions into an empty dataframe is not acceptable for backfill classification.

Normalized outcomes are:

- `succeeded`: eligible rows persisted or already identical.
- `no_data`: provider successfully returned an empty valid result.
- `insufficient_data`: stored bars cannot support required indicators.
- `provider_unavailable`: dependency/network/upstream availability failure.
- `schema_invalid`: required upstream columns cannot be normalized.
- `rate_limited` / `timeout`: retryable provider failure when detectable.
- `failed`: sanitized non-provider processing/database failure.

The service never substitutes yfinance, Tushare, mock, or static data. Existing provider-neutral service signatures remain, but this task accepts only `market=CN`, `provider=akshare` at the public full-market endpoint.

## 7. Coverage Contract

`GET /stock-selection/evidence-coverage?market=CN&provider=akshare` returns one typed projection used by API, CLI, and UI:

- universe identity: sync ID/as-of, active total, and SSE/SZSE/BSE counts;
- latest backfill: run ID, TaskRun ID, run kind/status, phase, cursor, total, timestamps, and provider;
- per evidence kind: ready, missing, no-data, insufficient, failed, coverage ratio, and threshold result;
- per exchange coverage for each evidence kind;
- freshness: latest evidence dates and stale counts;
- retry summary with counts and a bounded preview, not the entire internal retry list;
- sanitized diagnostics and safety metadata.

Readiness definitions:

- Daily bars: at least 35 valid daily rows in the requested window and a latest row within the 10-calendar-day freshness overlap at run end.
- Technical indicators: the latest stored daily-bar date has the selection-critical `ma`, `rsi`, and `mfi` rows; additional indicator availability is reported separately.
- Fundamentals: a latest snapshot exists with the selection-critical PE, revenue-growth, and net-margin fields present. Per-field ratios are also returned.

Acceptance thresholds are evaluated against active instruments: 95% bars, 90% critical indicators, 80% critical fundamentals, 100% classified outcomes, and non-empty ready coverage on every exchange.

## 8. API Contracts

Add thin FastAPI routes backed by services:

- `POST /ingestion/a-share-evidence-backfills`
  - Creates `baseline`, `canary`, or explicit incremental runs.
  - Validates AkShare/CN, evidence kinds, dates, batch size, and overlap protection before dispatch.
- `GET /ingestion/a-share-evidence-backfills/{run_id}`
  - Returns sanitized durable run state and linked TaskRun ID.
- `POST /ingestion/a-share-evidence-backfills/{run_id}/resume`
  - Starts a lineage-linked run from the stored phase/cursor.
- `POST /ingestion/a-share-evidence-backfills/{run_id}/retry-failed`
  - Starts a lineage-linked run using only the stored retry sets.
- `POST /ingestion/a-share-evidence-backfills/{run_id}/cancel`
  - Requests cooperative stop at the next checkpoint.
- `GET /stock-selection/evidence-coverage`
  - Returns the shared coverage projection.

Task name: `ingestion.backfill_a_share_research_evidence`.

Duplicate active runs for the same market/provider/run class return the existing run and an explicit `already_running` result rather than dispatching another worker. Invalid input is HTTP 400; unknown run IDs are HTTP 404; provider execution failures remain TaskRun/run diagnostics rather than synchronous API 500 responses.

## 9. Scheduling

- Set Celery timezone explicitly to `Asia/Shanghai` and retain UTC storage timestamps.
- Universe sync remains daily before evidence refresh.
- Weekday daily-bar/indicator incremental refresh starts at 18:30 with a 10-calendar-day overlap. Exchange holidays produce a classified no-new-session/skipped outcome, not fabricated rows.
- Fundamentals run as one deterministic shard per day (`shard_count=5`), rotating by local date.
- Beat calls a small schedule entry task that applies overlap protection before creating a TaskRun/backfill run.
- Schedules do not rerun the 18-month baseline.

## 10. Web Design

Extend `StockDiscoveryPanel` through a composed `AshareEvidenceCoveragePanel` rather than adding all state to the existing component.

- The server page fetches initial coverage with `cache: "no-store"`.
- The client component owns only pending/action messages and refreshes authoritative server state after mutations.
- New Next.js proxy routes preserve upstream status, content type, and `no-store` behavior.
- Coverage cards show totals and thresholds; an exchange table shows SSE/SZSE/BSE ratios.
- Progress shows phase, cursor/total, elapsed/updated time, failure/no-data counts, and provider.
- Guarded buttons start canary/baseline, resume, retry failed, and request cancellation.
- Every active/recent run links to the existing TaskRun detail page.
- English and Chinese labels are updated together; empty, error, partial, stale, and provider-failed states remain distinct.
- No delete/reset, arbitrary symbol payload, secret, raw exception, or database control is exposed.

## 11. Acceptance Runtime

Add an acceptance compose override/project that isolates state from the normal local stack:

- Docker Compose project name `stock-acceptance`.
- PostgreSQL database `stock_acceptance` with its own project-scoped volume.
- Dedicated Redis container/volume or isolated Redis DB in the acceptance project.
- Dedicated API/worker/beat ports and `APP_ENV=acceptance`.
- Web points at the acceptance API for browser checks.

Add a mutating acceptance runner with two explicit guards: real-network opt-in and acceptance-write confirmation. It validates that the configured database name is `stock_acceptance`, runs read-only provider preflight first, invokes public APIs, polls TaskRuns/backfill runs, and writes only sanitized JSON/Markdown evidence under the task evidence directory.

The runner records commit, migration head, dependency/provider versions, commands, timestamps, universe/exchange counts, canary/full-run coverage, corporate-action cursor/idempotency results, discovery timings, diagnostics, and browser evidence references. Connection strings, tokens, cookies, headers, and raw upstream payloads are excluded.

## 12. Compatibility and Rollback

- Existing single-symbol and explicit-symbol batch endpoints remain unchanged.
- Existing stock-discovery response fields remain additive; coverage endpoints are separate.
- Existing TaskRun rows with `heartbeat_at=NULL` use `started_at` fallback.
- The new migration is additive and has a downgrade path for the backfill table and heartbeat column.
- Disabling/removing Beat entries stops future runs without deleting evidence.
- Cancelling a run preserves committed evidence and checkpoint state.
- A code rollback can leave additive rows/tables unused; no existing market evidence is rewritten or deleted.

## 13. Security and Safety

- All diagnostics are sanitized and bounded.
- Task inputs contain provider/date/kind/cursor metadata only, never provider credentials.
- Acceptance artifacts redact connection details and never commit secrets.
- AI discovery remains deterministic-first; the backfill changes evidence availability, not ranking authority.
- No broker, order, position, target-price, or automated-trading behavior is introduced.
