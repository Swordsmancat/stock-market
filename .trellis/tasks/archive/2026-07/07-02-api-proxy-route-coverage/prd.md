# Add remaining API proxy route coverage

## Goal

Add focused route-level coverage for high-value Next.js API routes that did not yet have tests.
This slice locks down low-risk proxy/local route contracts before broader product changes.

## Requirements

- Cover selected low-side-effect routes:
  - `apps/web/app/api/instruments/route.ts`
  - `apps/web/app/api/alerts/triggers/recent/route.ts`
  - `apps/web/app/api/settings/route.ts`
- Verify backend proxy routes forward query parameters, preserve response status/content type, and use `cache: "no-store"`.
- Verify the settings route reads and writes through `platform-settings-store` without real filesystem I/O.
- Avoid changing backend contracts or runtime route behavior unless tests reveal a clear bug.

## Acceptance Criteria

- [x] Instruments route proxy success and failure behavior is covered.
- [x] Recent alert triggers route proxy success and failure behavior is covered.
- [x] Settings route GET/PUT behavior is covered with mocked store calls.
- [x] Focused web route tests pass.
- [x] Task is committed, pushed, archived, and the next backlog item is inspected.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
