# Hot Sector Production Breadth and Rotation History

## Goal

Upgrade hot-sector MVP toward professional CN/sector dashboards with verified production provider coverage, breadth metrics, constituent contribution, taxonomy governance, and rotation history.

## Requirements

- Build on `packages/services/hot_sectors.py`, `/sectors/hot`, the Next.js hot-sector proxy, and `HotSectors`.
- Verify at least one production-capable sector/fund-flow provider path or return explicit unavailable/degraded states with safe diagnostics.
- Add requirements for sector breadth: advancers/decliners, constituent contribution, and top positive/negative movers where provider data supports it.
- Add requirements for rotation history snapshots without presenting static fixtures as live fund-flow data.
- Preserve current taxonomy versioning, flow definition metadata, data-mode semantics, and top-constituent rendering.
- Document provider permission, quota, schema, and market-calendar assumptions.

## Acceptance Criteria

- [x] `design.md` defines provider capability matrix, breadth fields, constituent contribution fields, historical snapshot storage, and degraded-safe fallback behavior.
- [x] `implement.md` splits provider verification, backend normalization, frontend rendering, tests, and docs.
- [x] Provider failures and unknown providers still return typed unavailable/degraded payloads without leaking secrets.
- [x] Static fixtures remain clearly marked `degraded + mock`.
- [x] Frontend can render breadth/contribution/history data when present and a clear unavailable state when absent.
- [x] User and developer documentation explain flow definitions, provider delay, verification status, and historical limitations.

## Completion Notes

- Added additive hot-sector payload metadata for breadth, constituent contribution, taxonomy, rotation-history availability, and provider capability sections.
- Preserved degraded-safe behavior: static fixtures remain `degraded + mock`; unknown or failing providers return typed `unavailable` payloads with sanitized provider-error messages.
- Updated `HotSectors` to render breadth, contribution, taxonomy, and rotation-history metadata only when present, with unavailable copy for missing verified snapshots.
- Updated README, user guide, and developer maintenance docs to explain provider capability, data modes, breadth/contribution semantics, and current rotation-history limitations.
- Rotation-history persistence remains intentionally out of scope; current payload exposes explicit unavailable metadata rather than simulating historical data.

## Validation

- `python -m pytest tests/services/test_hot_sectors_service.py tests/api/test_sectors_api.py -q` -> `10 passed`
- `npm run test:web -- apps/web/app/api/hot-sectors/route.test.ts apps/web/components/hot-sectors.test.tsx` -> `10 passed`

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
