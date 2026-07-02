# Add task run detail API proxy route coverage

## Goal

Add focused route-level coverage for the Next.js task-run detail proxy route so task monitoring
pages have a locked-down backend forwarding contract without changing runtime behavior.

## Requirements

- Cover `apps/web/app/api/task-runs/[taskRunId]/route.ts`.
- Verify GET forwards the dynamic task-run identifier to the backend detail endpoint.
- Verify the proxy uses `cache: "no-store"`.
- Verify backend success and error responses preserve status, content type, and payload.
- Avoid backend API, database schema, worker, or UI behavior changes in this slice.

## Acceptance Criteria

- [x] Task-run detail GET success proxy behavior is covered.
- [x] Task-run detail GET failure proxy behavior is covered.
- [x] Route tests avoid real network calls by mocking `fetch`.
- [x] Focused web route tests pass.
- [x] Task is committed, pushed, archived, and the next backlog item is inspected.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
