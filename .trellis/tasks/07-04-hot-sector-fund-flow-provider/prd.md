# Hot Sector Fund Flow Provider

## Goal

Turn the existing hot-sector UI/fallback surface into a provider-backed sector rotation feature with explicit fund-flow definitions, sector classification, and degraded-safe fallback behavior.

## Requirements

- Define the sector taxonomy used by the product, including market coverage and symbol-to-sector mapping.
- Select and document provider sources for sector performance and fund-flow fields.
- Normalize sector payloads with source, provider, as-of time, flow metrics, top constituents, and availability metadata.
- Preserve degraded/unavailable states when provider data is missing, unsupported, or not verified.
- Avoid presenting demo, mock, or stale sector rankings as live fund-flow data.
- Add backend service/API tests and frontend route/component tests.
- Update user and developer manuals with the provider capability and flow definition.

## Acceptance Criteria

- [ ] Hot-sector payloads include verified sector performance and fund-flow fields for at least one provider or clearly degraded states.
- [ ] The UI distinguishes live/verified, delayed, demo, mock, and unavailable data.
- [ ] Sector classification and fund-flow definitions are documented.
- [ ] Tests cover provider data, unavailable provider, empty data, and UI degraded states.
- [ ] Documentation explains how users should interpret sector flow and its limitations.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
