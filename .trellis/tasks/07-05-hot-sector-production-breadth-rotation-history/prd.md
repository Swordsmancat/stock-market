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

- [ ] `design.md` defines provider capability matrix, breadth fields, constituent contribution fields, historical snapshot storage, and degraded-safe fallback behavior.
- [ ] `implement.md` splits provider verification, backend normalization, frontend rendering, tests, and docs.
- [ ] Provider failures and unknown providers still return typed unavailable/degraded payloads without leaking secrets.
- [ ] Static fixtures remain clearly marked `degraded + mock`.
- [ ] Frontend can render breadth/contribution/history data when present and a clear unavailable state when absent.
- [ ] User and developer documentation explain flow definitions, provider delay, verification status, and historical limitations.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
