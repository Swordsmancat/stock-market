# Add watchlist items API proxy route coverage

## Goal

Add focused route-level coverage for the Next.js watchlist item proxy route so product-facing
watchlist mutations are protected by low-risk tests without changing runtime behavior.

## Requirements

- Cover `apps/web/app/api/watchlist/items/route.ts`.
- Verify POST forwards request body, content type, backend status/content type, and uses `cache: "no-store"`.
- Verify DELETE forwards only the supported identity query parameters (`symbol` and `market`) and uses `cache: "no-store"`.
- Verify backend error responses are propagated without rewriting status, content type, or payload.
- Avoid backend API, database schema, provider, or UI behavior changes in this slice.

## Acceptance Criteria

- [x] Watchlist item POST success and failure proxy behavior is covered.
- [x] Watchlist item DELETE success and failure proxy behavior is covered.
- [x] Route tests avoid real network calls by mocking `fetch`.
- [x] Focused web route tests pass.
- [x] Task is committed, pushed, archived, and the next backlog item is inspected.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
