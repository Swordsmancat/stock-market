# Persist TaskRun quality diagnostics

## Goal

Persist ingestion `quality_diagnostics` into successful ingestion TaskRun result payloads without changing TaskRun lifecycle semantics.

## Requirements

- Use the archived design `.trellis/tasks/archive/2026-07/07-02-design-taskrun-quality-diagnostics/design.md` as the source of truth.
- Update the ingestion worker result payload after ingestion single-fetch has stabilized the snapshot contract.
- Preserve existing top-level ingestion result fields: `market`, `instrument_count`, `bar_count`, `status`, and `provider`.
- Add `quality_diagnostics` under `TaskRun.result_json` for successful ingestion worker runs.
- Do not make diagnostics `WARN` or `FAIL` change TaskRun technical status to failed.
- Preserve retry semantics: retries create new TaskRuns and do not copy previous `result_json`.
- Preserve report lineage and non-ingestion task result payloads.
- Avoid database schema changes.

## Acceptance Criteria

- [x] Successful ingestion worker TaskRuns persist `result_json.quality_diagnostics`.
- [x] Existing compact ingestion result fields remain present and compatible.
- [x] Diagnostics `WARN` and `FAIL` can be persisted while TaskRun status remains `succeeded` when worker execution succeeds.
- [x] Retry behavior remains based on `input_json.retry_of` and does not copy previous result payloads.
- [x] Report task result payloads and report `task_run_id` lineage are not regressed.
- [x] Focused TaskRun/task dispatch tests pass.

## Validation

```bash
python -m pytest tests/services/test_task_runs_service.py tests/services/test_task_dispatch.py -v
```

## Notes

- Expected production file: `apps/worker/tasks/ingestion.py`.
- Service tests may touch `packages/services/task_runs.py` behavior only if needed.
- This child should run after ingestion single-fetch.
