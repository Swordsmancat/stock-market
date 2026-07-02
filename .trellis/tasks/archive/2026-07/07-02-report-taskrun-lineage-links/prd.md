# Improve report task-run lineage links

## Goal

Improve frontend report lineage navigation by allowing a TaskRun detail page to link back to every
generated report recorded in its result payload. This preserves the existing single-report path and
adds support for watchlist analysis runs that create multiple reports in one task.

## Requirements

- Preserve the existing single report link from `result_json.report.id`.
- Add support for report links under `result_json.items[].report.id` for watchlist refresh runs.
- Deduplicate repeated report IDs so retries or repeated result entries do not render duplicate links.
- Include symbol context in generated report link labels when the report object provides a symbol.
- Avoid backend API or database changes in this slice.

## Acceptance Criteria

- [x] TaskRun detail still links a single generated report.
- [x] TaskRun detail links multiple generated reports from watchlist task results.
- [x] Duplicate report IDs render only once.
- [x] Focused frontend page tests pass.
- [x] Task is committed, pushed, archived, and the next backlog item is inspected.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
