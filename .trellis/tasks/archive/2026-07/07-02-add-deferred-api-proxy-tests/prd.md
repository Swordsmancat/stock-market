# Add deferred API proxy tests

## Goal

Complete the previously deferred Lane E by adding focused frontend tests for high-value API proxy or client interaction behavior without changing backend contracts.

## Requirements

- Inspect existing frontend API route proxies, client components, and Vitest patterns.
- Select one or two high-value API proxy routes or one API proxy plus one client interaction with clear regression value.
- Keep changes limited to frontend tests and minimal test-support adjustments.
- Do not change backend API contracts or backend Python code.
- Do not perform broad UI rewrites or i18n cleanup outside the selected tests.
- Run `npm run test:web`.

## Acceptance Criteria

- [x] At least one high-value API proxy or client interaction path has focused test coverage.
- [x] Tests cover request forwarding or user-visible interaction behavior, not only static rendering.
- [x] No backend Python files are modified.
- [x] No unrelated frontend page rewrites are included.
- [x] `npm run test:web` passes.
- [x] The implementation report identifies selected route/component and why it was chosen.

## Notes

- This task completes the deferred Lane E from `.trellis/tasks/07-02-parallel-backlog-execution/implement.md`.
