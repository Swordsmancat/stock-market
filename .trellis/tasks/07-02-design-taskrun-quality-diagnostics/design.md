# TaskRun Quality Diagnostics Design

## Status

- Scope: design only.
- Production code changes: no.
- Target artifact: `.trellis/tasks/07-02-design-taskrun-quality-diagnostics/design.md`.

## Problem statement

`packages.services.ingestion.ingest_market_snapshot()` already builds `quality_diagnostics` in the returned snapshot, but the Celery ingestion task currently strips that field before calling `finish_task_run()`. As a result, TaskRun detail pages show ingestion counts and status but not the per-instrument data-quality result that operators need for post-run diagnosis.

The design must persist ingestion quality diagnostics in `TaskRun.result_json` and display them in the TaskRun detail UI without changing report lineage, task-run retry behavior, or existing generic TaskRun API shapes.

## Current TaskRun result flow

### Data model

- `packages/domain/models.py`
  - `TaskRun.result_json` is a nullable JSON/JSONB column.
  - `TaskRun.input_json` stores the original dispatch inputs.
  - `TaskRun.status` is string-based (`running`, `succeeded`, `failed`).
  - `GeneratedReport.task_run_id` is an optional FK to `task_runs.id`, which is the current report lineage link.

### Start / enqueue / dispatch

- `packages/services/task_runs.py`
  - `start_task_run(task_name, input_json, session)` creates a `TaskRun` with:
    - `status="running"`
    - `started_at=now`
    - `input_json=input_json`
    - no `result_json` yet.
  - `enqueue_task_run(task_name, input_json, session)`:
    1. expires stale running task runs;
    2. creates a DB `TaskRun` via `start_task_run()`;
    3. rejects unsupported task names using `is_dispatchable_task()`;
    4. dispatches Celery via `dispatch_task_run(task_name, input_json, task_run_id)`;
    5. stores `celery_task_id` on the same `TaskRun` row;
    6. returns `{source, status, task_run, celery_task_id}`.
  - If dispatch is unsupported or raises, the newly-created TaskRun is failed via `fail_task_run()` and the response uses `dispatch_failed` / `retry_dispatch_failed` style wrapper statuses.

- `packages/services/task_dispatch.py`
  - `_DISPATCHERS` maps logical task names to Celery task modules.
  - `ingestion.ingest_market_data` dispatches to `apps.worker.tasks.ingestion.ingest_market_data.delay(...)` and passes `task_run_id` through unchanged.
  - Report tasks and alert tasks follow the same `task_run_id` handoff pattern.

### Worker task result

- `apps/worker/tasks/ingestion.py`
  - `ingest_market_data(...)` resolves date/provider defaults and opens `SessionLocal()`.
  - If `task_run_id` is provided, it loads that existing `TaskRun` by UUID. If absent, it creates a new one with `start_task_run()` for direct Celery/manual calls.
  - It calls `packages.services.ingestion.ingest_market_snapshot(...)`, which returns a full snapshot including `quality_diagnostics`.
  - It currently builds a compact `result_payload` with only:
    - `market`
    - `instrument_count`
    - `bar_count`
    - `status`
    - `provider`
  - It calls `finish_task_run(task_run, result_payload, session)` and returns the same compact payload.
  - On exception it calls `fail_task_run(task_run, str(exc), session)` and re-raises.

- `apps/worker/tasks/reports.py`
  - Report tasks also load an existing `TaskRun` when `task_run_id` is supplied, otherwise create one.
  - `refresh_daily_stock_analysis()` passes `task_run.id` into `refresh_stock_analysis(...)`, which ultimately allows generated reports to keep their `task_run_id` lineage.
  - Report tasks call `finish_task_run(task_run, result, session)` with report result payloads containing report IDs and statuses.

### Finish / fail / stale expiry

- `packages/services/task_runs.py`
  - `finish_task_run(task_run, result_json, session)` mutates the existing row:
    - `status="succeeded"`
    - `finished_at=now`
    - `duration_ms` from `started_at` to `finished_at`
    - `result_json=result_json`
    - `error_message=None`
    - returns `_serialize_task_run(task_run)`.
  - `fail_task_run(task_run, error_message, session)` mutates the existing row:
    - `status="failed"`
    - `finished_at=now`
    - `duration_ms` computed similarly
    - `error_message=error_message`
    - leaves `result_json` as-is / unset for ordinary failures.
  - `expire_stale_task_runs()` marks old running rows failed with a timeout message; it does not create retries or result payloads.

### Retry

- `packages/services/task_runs.py`
  - `retry_task_run_payload(session, task_run_id)` loads the original row by UUID.
  - It creates a new TaskRun through `enqueue_task_run()` using:
    ```json
    {
      "...original.input_json": "...",
      "retry_of": "<original task_run id>"
    }
    ```
  - Retry does not mutate the original TaskRun.
  - Retry lineage is represented in the new TaskRun `input_json.retry_of`, not by copying original `result_json`.
  - Successful retry enqueue returns wrapper status `retry_started` and `item=<new task_run>`; dispatch failure returns `retry_dispatch_failed` and `item=<failed new task_run>`.

### API payload

- `apps/api/routers/task_runs.py`
  - `GET /task-runs/recent` returns `get_recent_task_runs_payload()` as `{source, items}`.
  - `GET /task-runs/latest?task_name=...` returns a serialized TaskRun merged with `{source}` or not-found metadata.
  - `GET /task-runs/{task_run_id}` returns `{source, item}` from `get_task_run_payload()` or 404.
  - `POST /task-runs/{task_run_id}/retry` returns retry wrapper payloads from `retry_task_run_payload()` or 404.

- Serialization is centralized in `_serialize_task_run()` and already includes `result_json` unchanged, so nested diagnostics can flow through the API without schema/database migration.

### Frontend detail payload

- `apps/web/app/[locale]/task-runs/[taskRunId]/page.tsx`
  - `TaskRunDetail.result_json` is typed as `Record<string, unknown> | null`.
  - `fetchTaskRun()` accepts both the current wrapped API payload `{item}` and legacy/direct TaskRun-shaped payloads.
  - The detail page currently displays:
    - task name/status badge;
    - start time/duration;
    - Celery task ID;
    - raw `input_json`;
    - raw `result_json`;
    - generated report link extracted from `result_json.report.id`;
    - error message;
    - retry button only when `taskRun.status === "failed"`.
  - Because `result_json` is displayed raw today, adding `result_json.quality_diagnostics` is backward compatible even before a polished UI section lands.

## Proposed `result_json.quality_diagnostics` contract

Persist diagnostics under the ingestion task result payload as:

```json
{
  "market": "US",
  "instrument_count": 1,
  "bar_count": 2,
  "status": "ingested",
  "provider": "mock",
  "quality_diagnostics": {
    "status": "OK",
    "instrument_count": 1,
    "instruments": [
      {
        "symbol": "AAPL",
        "status": "OK",
        "checked_bars": 2,
        "missing_dates": [],
        "invalid_ohlc": [],
        "volume_warnings": [],
        "quality_error": null
      }
    ],
    "errors": [],
    "warnings": []
  }
}
```

### Top-level ingestion result fields

Keep existing fields unchanged to avoid breaking existing assertions and consumers:

- `market: string`
- `instrument_count: number`
- `bar_count: number`
- `status: "ingested" | string`
- `provider: string`

Add only:

- `quality_diagnostics: QualityDiagnostics`

### `QualityDiagnostics`

Recommended stable contract:

```ts
type QualityStatus = "OK" | "WARN" | "FAIL";

type QualityDiagnostics = {
  status: QualityStatus;
  instrument_count: number;
  instruments: InstrumentQualityDiagnostics[];
  errors?: QualityIssue[];
  warnings?: QualityIssue[];
  quality_error?: string;
};
```

Field guidance:

- `status`
  - `OK`: every instrument quality check is OK.
  - `WARN`: at least one warning exists and no instrument is failed.
  - `FAIL`: no instruments, a quality checker exception occurred, or at least one instrument failed.
- `instrument_count`
  - Count of instruments represented in `instruments`.
  - Should usually match the top-level result `instrument_count`, but the UI should not rely on exact equality because diagnostics may be partial after provider/quality-check edge cases.
- `instruments`
  - One entry per instrument when available.
- `errors`
  - Optional normalized summary list for UI convenience.
  - Should include no-instrument failures and per-instrument hard failures.
- `warnings`
  - Optional normalized summary list for UI convenience.
  - Should include missing-date warnings, volume warnings, and any other non-fatal quality concerns.
- `quality_error`
  - Kept for compatibility with the current no-instruments shape and quality-check exception handling in `packages/services/ingestion.py`.
  - Prefer also mirroring it into `errors` for UI rendering.

### `InstrumentQualityDiagnostics`

The current ingestion service already returns per-instrument payloads produced by `check_daily_bar_quality(...).to_dict()` plus `symbol`. Preserve those fields and treat them as the initial public shape:

```ts
type InstrumentQualityDiagnostics = {
  symbol: string | null;
  status: QualityStatus;
  checked_bars: number;
  missing_dates: string[];
  invalid_ohlc: unknown[];
  volume_warnings: unknown[];
  quality_error?: string;
};
```

Recommended forward-compatible normalization:

- Keep `missing_dates`, `invalid_ohlc`, and `volume_warnings` as the source-specific/raw detail arrays currently produced by `data_quality`.
- Add normalized top-level `errors` / `warnings` only as summaries, not replacements, so no existing diagnostics detail is lost.
- The frontend should defensively parse unknown arrays and render unknown issue objects with `JSON.stringify()` fallback.

### `QualityIssue`

Recommended summary shape:

```ts
type QualityIssue = {
  symbol?: string | null;
  code: string;
  message: string;
  count?: number;
  details?: unknown;
};
```

Suggested codes:

- `NO_INSTRUMENTS`
- `QUALITY_CHECK_ERROR`
- `MISSING_DATES`
- `INVALID_OHLC`
- `VOLUME_WARNING`

This summary shape is optional for the first implementation if it requires too much refactoring. Minimum acceptable first increment is to persist the existing `snapshot["quality_diagnostics"]` exactly, then let the frontend derive warnings/errors from `instruments`, `quality_error`, `missing_dates`, `invalid_ohlc`, and `volume_warnings`.

## Backend integration points

### Primary change: ingestion worker result payload

Implement in `apps/worker/tasks/ingestion.py` inside `ingest_market_data()` after `snapshot = ingest_market_snapshot(...)`.

Current compact payload:

```python
result_payload = {
    "market": str(snapshot["market"]),
    "instrument_count": int(snapshot["instrument_count"]),
    "bar_count": int(snapshot["bar_count"]),
    "status": str(snapshot["status"]),
    "provider": provider_value,
}
```

Recommended payload:

```python
quality_diagnostics = snapshot.get("quality_diagnostics")
result_payload = {
    "market": str(snapshot["market"]),
    "instrument_count": int(snapshot["instrument_count"]),
    "bar_count": int(snapshot["bar_count"]),
    "status": str(snapshot["status"]),
    "provider": provider_value,
    "quality_diagnostics": quality_diagnostics if isinstance(quality_diagnostics, dict) else None,
}
```

Preferred stricter behavior:

- If `quality_diagnostics` is unexpectedly absent, persist a conservative diagnostic block instead of `None`:
  ```json
  {
    "status": "FAIL",
    "instrument_count": 0,
    "instruments": [],
    "errors": [{"code": "QUALITY_DIAGNOSTICS_MISSING", "message": "Ingestion completed without quality diagnostics."}]
  }
  ```
- Do not fail the TaskRun solely because diagnostics are `WARN` or `FAIL`; diagnostics describe data quality, while TaskRun status describes whether the ingestion task completed technically.

### Avoid changing `finish_task_run()` semantics

Do not make `finish_task_run()` inspect or special-case `quality_diagnostics`.

Rationale:

- `finish_task_run()` is a generic persistence helper used by ingestion, report, and alert workers.
- Its current job is to mark a task as succeeded and store an arbitrary JSON result.
- Changing its behavior based on a nested ingestion-specific key would risk surprising report/alert tasks and retry tests.

### API changes

No backend route or serialization change is required for the first implementation:

- `_serialize_task_run()` already returns `result_json` as stored.
- `GET /task-runs/{task_run_id}` already returns `{source, item}` with `item.result_json`.
- `GET /task-runs/recent` and `/latest` will also include diagnostics automatically for ingestion rows.

Optional API follow-up, not required now:

- Add typed response models if the project later formalizes FastAPI schemas.
- Add a small service-level helper to parse/normalize diagnostics for API-specific presentation only if multiple frontend clients need the same derived summaries.

## Frontend TaskRun detail display

Add a dedicated `Quality Diagnostics` section in `apps/web/app/[locale]/task-runs/[taskRunId]/page.tsx` that appears only when `taskRun.result_json?.quality_diagnostics` is an object.

### Defensive parsing

Because `result_json` is `Record<string, unknown> | null`, add local helper functions/types in the page or a colocated component:

- `extractQualityDiagnostics(resultJson): QualityDiagnostics | null`
- `normalizeQualityStatus(value): "OK" | "WARN" | "FAIL" | null`
- `extractQualityIssues(diagnostics): { errors: RenderableIssue[]; warnings: RenderableIssue[] }`

The UI must not throw if old TaskRuns have no diagnostics or if a future provider adds extra fields.

### Badge

Render a diagnostics-specific badge independent from `taskRun.status`:

- `OK`: default/positive badge, text `OK`.
- `WARN`: secondary or warning-styled badge, text `WARN`.
- `FAIL`: destructive badge, text `FAIL`.

Important distinction:

- TaskRun badge remains `succeeded` / `failed` / `running`.
- Quality badge is nested data quality, so a TaskRun can be `succeeded` with quality `FAIL` if ingestion completed but the data is unusable or empty.

### Instrument summary

Show a compact summary before raw JSON:

- `Status: OK/WARN/FAIL`
- `Instruments checked: <quality_diagnostics.instrument_count>`
- Optional cross-check: `Task result instruments: <result_json.instrument_count>`
- Per-instrument rows/cards with:
  - symbol;
  - status badge;
  - checked bar count;
  - counts for missing dates, invalid OHLC rows, volume warnings;
  - quality error if present.

Recommended table/card columns:

| Symbol | Status | Checked bars | Missing dates | Invalid OHLC | Volume warnings |
| --- | --- | ---: | ---: | ---: | ---: |

For small payloads, include expandable/detail lists below each instrument. For large payloads, render counts first and keep raw `result_json` as the complete fallback.

### Failure and warning lists

Render two optional lists:

- `Errors`
  - top-level `quality_error`;
  - top-level `errors[]`;
  - instrument `quality_error`;
  - non-empty `invalid_ohlc` when instrument status is `FAIL`;
  - no-instrument diagnostics.
- `Warnings`
  - top-level `warnings[]`;
  - non-empty `missing_dates`;
  - non-empty `volume_warnings`;
  - any non-fatal instrument issue.

Each list item should include the symbol when available and a concise message. Unknown issue objects can be rendered as prettified JSON in a small `<pre>` or stringified text.

### Raw result JSON remains

Keep the existing raw `result_json` block after the polished diagnostics section.

Rationale:

- Operators still need full provider/debug payloads.
- It preserves backward compatibility and reduces risk if the first UI parser misses a field.

### Translations

Add TaskRuns messages in both English and Chinese message files during implementation. Likely keys:

- `qualityDiagnostics`
- `qualityStatus`
- `qualityStatusOk`
- `qualityStatusWarn`
- `qualityStatusFail`
- `instrumentsChecked`
- `taskResultInstruments`
- `checkedBars`
- `missingDates`
- `invalidOhlc`
- `volumeWarnings`
- `qualityErrors`
- `qualityWarnings`
- `noQualityDiagnostics`

If the implementation wants to avoid adding a `noQualityDiagnostics` empty state, simply omit the section when absent.

## Compatibility with report lineage and retry semantics

### Report lineage

This design does not change report lineage.

- `GeneratedReport.task_run_id` remains the lineage field.
- Report generation tasks continue passing `task_run.id` into report services.
- Report result payloads keep their existing `result_json.report` / `result_json.items[].report` shapes.
- `extractReportId()` on the detail page should remain focused on `result_json.report.id`; quality diagnostics must not be stored under `report` or alter report IDs.
- Ingestion TaskRuns normally do not create reports, so adding `quality_diagnostics` to ingestion results cannot break report links.

### Retry

This design does not change retry behavior.

- Retrying still creates a new TaskRun row.
- The new retry row still receives original `input_json` plus `retry_of`.
- The original TaskRun remains immutable except for its already-recorded fields.
- The retry does not copy old `result_json.quality_diagnostics`; the retried worker writes a fresh result based on the new ingestion attempt.
- If retry dispatch fails, the new retry row is failed before worker execution and will not have quality diagnostics unless a future dispatch path explicitly adds them. The UI must handle missing diagnostics.

### Task status semantics

Do not map quality `FAIL` to TaskRun `failed` unless ingestion itself raises an exception.

Reasoning:

- Existing ingestion service explicitly catches quality-check exceptions and surfaces them in diagnostics "without interrupting ingestion".
- Operators need to distinguish infrastructure/task failure from completed ingestion with poor data quality.
- Existing tests expect successful ingestion task runs when the worker completes and stores bars/counts.

## Required tests

### Services: `tests/services/test_task_runs_service.py`

Add or update focused tests around generic JSON persistence, not ingestion-specific logic:

- `finish_task_run` persists nested `quality_diagnostics` unchanged in `result_json`.
- `get_latest_task_run_payload` and/or `get_task_run_payload` returns the nested diagnostics unchanged.
- Retry creates a new running task with `retry_of` and does not copy the old diagnostics into `input_json` or otherwise mutate the old row.

These tests ensure TaskRun service remains a transparent JSON store.

### Worker / task dispatch: `tests/services/test_task_dispatch.py` and `tests/worker/test_tasks.py`

`tests/services/test_task_dispatch.py`:

- Existing `test_dispatch_task_run_enqueues_market_ingestion` should remain unchanged unless function arguments change; it should continue asserting `task_run_id` is passed.
- No diagnostics assertion belongs here because dispatch only enqueues, it does not execute ingestion.

`tests/worker/test_tasks.py`:

- Extend `test_ingest_market_data_records_succeeded_task_run` to assert:
  - returned worker result includes `quality_diagnostics`;
  - latest TaskRun `result_json.quality_diagnostics.status == "OK"` for mock data;
  - per-instrument diagnostics include `symbol`, `checked_bars`, and empty warning/error arrays.
- Add a test for diagnostics `FAIL` without worker exception using a monkeypatched empty snapshot or ingestion service result:
  - TaskRun status remains `succeeded`;
  - `result_json.quality_diagnostics.status == "FAIL"`;
  - top-level TaskRun `error_message is None`.
- Add a test for existing `task_run_id` reuse if needed:
  - worker updates the existing row with diagnostics rather than creating a second row.

### Ingestion service: `tests/services/test_ingestion_service.py`

Existing tests already cover:

- successful snapshot includes `quality_diagnostics` with `OK`;
- no instruments yields `FAIL` and `quality_error`;
- compatibility of mock ingestion.

If normalized `errors` / `warnings` are added in `packages/services/ingestion.py`, update/add tests for:

- top-level `errors` includes `NO_INSTRUMENTS` on empty snapshot;
- top-level `warnings` summarizes volume/missing-date warnings when present;
- existing per-instrument arrays remain present.

If implementation only persists the existing service output, no service test change is required beyond worker persistence tests.

### API: `tests/api/test_task_runs_api.py` and `tests/api/test_ingestion_api.py`

`tests/api/test_task_runs_api.py`:

- Add detail endpoint assertion that a TaskRun finished with nested `quality_diagnostics` returns the exact nested object under `detail["item"]["result_json"]["quality_diagnostics"]`.
- Keep existing wrapped payload shape `{source, item}`.

`tests/api/test_ingestion_api.py`:

- Extend `test_ingestion_api_dispatches_task_run_and_writes_database` to assert the synchronous dispatch response's `task_run.result_json.quality_diagnostics.status == "OK"`.
- Assert existing fields (`status`, `market`, `bar_count`) still exist unchanged.

### Frontend detail: `apps/web/app/[locale]/task-runs/[taskRunId]/page.test.tsx`

Add tests for:

- `OK` diagnostics render:
  - diagnostics section heading;
  - `OK` badge/text;
  - instrument count;
  - instrument symbol and checked bar count.
- `WARN` diagnostics render warning counts/list:
  - e.g. non-empty `missing_dates` or `volume_warnings`.
- `FAIL` diagnostics render destructive/failure text:
  - e.g. no instruments `quality_error` or instrument `quality_error`.
- Old payloads without `quality_diagnostics` still render raw result JSON and generated report link without throwing.
- Existing generated report link behavior remains unchanged.

## Recommended implementation order

1. Worker persistence only
   - Add `quality_diagnostics` to `apps/worker/tasks/ingestion.py` `result_payload`.
   - Keep all existing result fields unchanged.
   - Add/adjust worker and ingestion API tests.

2. Service/API regression coverage
   - Add a TaskRun service test for transparent nested JSON persistence if not already covered by worker/API tests.
   - Add TaskRun API detail assertion for nested diagnostics.

3. Frontend parser and UI section
   - Add local defensive parsing helpers/types.
   - Render diagnostics badge, summary, instrument rows, errors, warnings.
   - Keep raw JSON block.
   - Add frontend tests for OK/WARN/FAIL and missing diagnostics.

4. Optional normalization follow-up
   - Add top-level `errors` / `warnings` in `packages/services/ingestion.py` only if the UI would otherwise duplicate too much derivation logic.
   - Preserve existing per-instrument fields and `quality_error` for compatibility.

5. Manual verification
   - Trigger mock ingestion through the API.
   - Open the TaskRun detail page.
   - Confirm TaskRun status, quality badge, raw JSON, and retry button behavior.

## Rollback plan

### Backend rollback

- Revert the worker payload addition of `quality_diagnostics`.
- Because there is no schema migration, rollback is code-only.
- Existing rows that already contain `result_json.quality_diagnostics` can remain in the database; old code and current API serialization tolerate extra JSON keys.

### Frontend rollback

- Hide/remove the diagnostics UI section and parsing helpers.
- Keep the raw result JSON block; users can still inspect persisted diagnostics manually if backend data remains.

### Partial rollout safety

- Backend first, frontend later is safe: raw JSON already displays diagnostics.
- Frontend first, backend later is safe if parser treats missing diagnostics as `null` and omits the section.
- Mixed old/new TaskRuns are safe because `quality_diagnostics` is optional.

## Key decisions

- Persist diagnostics only under ingestion `result_json.quality_diagnostics`.
- Keep TaskRun `status` lifecycle unchanged; data quality `FAIL` is not the same as worker failure.
- Do not change generic TaskRun service or API payload wrappers.
- Do not change report lineage fields or report result shapes.
- Retry creates a fresh TaskRun and fresh diagnostics on execution; it does not copy previous diagnostics.
