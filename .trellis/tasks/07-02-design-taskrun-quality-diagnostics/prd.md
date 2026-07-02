# Design TaskRun quality diagnostics

## Goal

Design how ingestion `quality_diagnostics` should be persisted into TaskRun results and displayed in the TaskRun detail UI without breaking existing TaskRun/report lineage behavior.

## Requirements

- Map current TaskRun creation, completion, retry, and result JSON flows.
- Define a stable result JSON contract for quality diagnostics.
- Define how TaskRun detail UI should display diagnostics for OK/WARN/FAIL states.
- Identify backend, frontend, and worker tests required before implementation.
- Preserve existing report/task_run lineage and retry semantics.
- Prefer a design artifact only; do not modify production code in this task unless explicitly approved later.

## Acceptance Criteria

- [ ] Current TaskRun result flow is documented with file/function references.
- [ ] Proposed `quality_diagnostics` result contract is documented.
- [ ] TaskRun detail UI display shape is documented.
- [ ] Required backend and frontend tests are listed.
- [ ] Compatibility with existing report lineage and retry behavior is addressed.
- [ ] No production code is modified by this design-only task.

## Notes

- Design-only child task; expected output may be `design.md` inside this task directory.
- Later implementation may touch `packages/services/task_runs.py`, worker tasks, task-run API, and task-run detail UI/tests.
