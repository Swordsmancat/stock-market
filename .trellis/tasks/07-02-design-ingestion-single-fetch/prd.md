# Design ingestion single fetch

## Goal

Design a minimal refactor path for ingestion so real providers are fetched once, and the same snapshot drives API return payloads, database writes, and quality diagnostics.

## Requirements

- Map the current ingestion data flow from provider snapshot to database write and returned payload.
- Identify exactly where duplicate provider fetches occur.
- Propose a minimal implementation plan that avoids duplicate fetches while preserving existing public behavior.
- Identify tests required before implementation.
- Prefer a design artifact only; do not modify ingestion implementation in this task unless explicitly approved later.
- Keep the design compatible with existing `quality_diagnostics` behavior.

## Acceptance Criteria

- [ ] Current double-fetch flow is documented with file/function references.
- [ ] Proposed single-fetch data flow is documented.
- [ ] Backward compatibility and migration risks are listed.
- [ ] Required service tests are listed.
- [ ] The design clarifies how `quality_diagnostics`, `bar_count`, and database writes share the same snapshot.
- [ ] No production code is modified by this design-only task.

## Notes

- Design-only child task; expected output may be `design.md` inside this task directory.
- Later implementation would likely touch `packages/services/ingestion.py` and `tests/services/test_ingestion_service.py`.
