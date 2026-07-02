# Expand proxy client interaction tests

## Goal

Add focused coverage for one additional high-value frontend API proxy or client interaction path without changing backend contracts.

## Requirements

- Choose a path that does not overlap TaskRun detail diagnostics UI files.
- Prefer route-handler proxy tests under `apps/web/app/api/**/route.test.ts` when they provide clear regression value.
- If selecting a client interaction, keep it focused on user-visible behavior and mock network/backend boundaries.
- Cover request forwarding, upstream status/payload propagation, or user-visible success/failure behavior.
- Do not change backend Python code, backend API contracts, or broad UI layout.
- Keep tests deterministic and independent of live backend services.

## Acceptance Criteria

- [x] At least one additional API proxy or client interaction path has focused coverage.
- [x] The test asserts meaningful forwarding or user-visible interaction behavior.
- [x] Backend contracts and backend Python files are unchanged.
- [x] The selected test files do not overlap the TaskRun detail diagnostics UI lane.
- [x] `npm run test:web` passes.
- [x] The implementation notes identify the selected route/component and why it was chosen.

## Validation

```bash
npm run test:web
```

## Notes

- Existing proxy coverage includes task-run retry route tests.
- Candidate route proxies include settings, ingestion snapshot, reports generation, instruments, portfolios, watchlist items, and alerts triggers.
