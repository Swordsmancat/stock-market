# Complete Ingestion Diagnostics Backlog Design

## Scope

This implementation wave turns the archived ingestion diagnostics designs into production changes and tests. It keeps the public ingestion snapshot shape, TaskRun API wrappers, retry semantics, and report lineage stable.

## Workstream Boundaries

### Lane A: Ingestion single-fetch

Primary files:

- `packages/services/ingestion.py`
- `tests/services/test_ingestion_service.py`
- `tests/services/test_data_quality.py`

Design source:

- `.trellis/tasks/archive/2026-07/07-02-design-ingestion-single-fetch/design.md`

This lane owns the data consistency foundation. It must complete before TaskRun diagnostics are persisted as operator-facing evidence.

### Lane B: TaskRun diagnostics persistence

Primary files:

- `apps/worker/tasks/ingestion.py`
- `packages/services/task_runs.py` if service-level serialization tests need updates
- `tests/services/test_task_runs_service.py`
- `tests/services/test_task_dispatch.py`

Design source:

- `.trellis/tasks/archive/2026-07/07-02-design-taskrun-quality-diagnostics/design.md`

This lane depends on Lane A's ingestion result contract being stable.

### Lane C: TaskRun detail diagnostics UI

Primary files:

- `apps/web/app/[locale]/task-runs/[taskRunId]/page.tsx`
- `apps/web/messages/en.json`
- `apps/web/messages/zh.json`
- colocated TaskRun detail page tests

This lane may prepare defensive parsing from fixture data in parallel, but final assertions should match the backend result shape from Lane B.

### Lane D: Additional proxy/client interaction tests

Primary files should avoid Lane C's TaskRun detail page files. Preferred candidates are API route-handler proxy tests under:

- `apps/web/app/api/**/route.test.ts`

This lane can run in parallel with Lane A because it does not touch backend ingestion files.

## Data Flow

Target ingestion flow:

```text
provider fetch once
  -> serialized snapshot
      -> returned ingestion payload
      -> database write
      -> bar_count
      -> quality_diagnostics
      -> worker TaskRun result_json.quality_diagnostics
      -> TaskRun detail diagnostics UI
```

The important invariant is that every downstream diagnostic display is traceable to the same snapshot that was written and returned.

## Compatibility Rules

- Keep `get_market_snapshot(...)` public behavior unchanged.
- Keep ingestion response top-level fields compatible: `market`, `instrument_count`, `bar_count`, `status`, `provider`, and `quality_diagnostics`.
- Keep `TaskRun.status` as technical execution status. Data-quality `WARN` or `FAIL` must not automatically make the worker fail.
- Keep retry lineage in `input_json.retry_of`; do not copy previous `result_json` into retries.
- Keep generated report lineage through existing `task_run_id` behavior.
- Keep raw `result_json` visible in the frontend detail page as a fallback.

## Parallel Strategy

- Start Lane A and Lane D in parallel.
- Hold Lane B until Lane A is implemented or its result contract is confirmed.
- Lane C can start as fixture-based UI prep, but final integration must wait for Lane B.
- Main agent owns Trellis task-state updates, review consolidation, final commit, and any push.
- Subagents must not commit or push.

## Risk Controls

- Add tests before or alongside the ingestion writer refactor to prove provider fetch counts.
- Convert serialized numeric values to database numeric values safely, for example with `Decimal(str(value))`.
- Parse serialized timestamps explicitly and fail loudly on unsupported values.
- Use defensive frontend parsing because `result_json` is untrusted JSON.
- Keep selected proxy/client tests focused to avoid unrelated UI churn.
