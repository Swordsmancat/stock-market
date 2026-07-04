# Hot Sector Fund Flow Provider Implementation Plan

## Slice 1: Backend Contract and Service Boundary

1. Add `packages/services/hot_sectors.py` with:
   - versioned MVP taxonomy
   - provider result types / protocol
   - static degraded fixture provider
   - provider-backed normalization helper
   - unavailable/no-data/degraded payload builders
2. Refactor `apps/api/routers/sectors.py` to remain a thin FastAPI router delegating to the service.
3. Keep `GET /sectors/hot` path and `limit` validation unchanged.
4. Preserve legacy response fields used by the dashboard while adding provider, as-of, availability, flow definition, delayed, taxonomy, and top constituent metadata.
5. Add backend tests for:
   - static fixture fallback remains `degraded + mock`
   - injected provider success returns `ok + live`
   - injected delayed provider returns `ok + delayed`
   - empty provider response returns no fabricated sectors
   - unsupported provider returns typed unavailable/degraded payload

## Slice 2: Frontend Contract and UI States

1. Extend `HotSectorsDataMode` to include `delayed`.
2. Extend dashboard and Next API proxy payload types with optional provider/as-of/availability/flow definition/top constituent fields.
3. Harden `HotSectors` against null numeric fields.
4. Replace Chinese-string-only flow direction checks with provider-neutral `flow_direction` fallback logic.
5. Render provider/as-of/flow definition metadata and top constituents when available.
6. Add explicit badge/warning states for live, delayed, demo, mock, and unavailable.
7. Update `apps/web/messages/en.json` and `apps/web/messages/zh.json` with new status and metadata labels.
8. Add focused tests for:
   - component live provider data
   - component delayed provider data
   - component mock warning / degraded state
   - component unavailable empty state
   - Next API proxy provider metadata passthrough and rejected backend fetch
   - dashboard integration remains stable

## Slice 3: Documentation and Roadmap Updates

1. Update `docs/manual/user-guide.md` to explain the provider-backed MVP, data modes, delayed data, mock/demo warnings, and fund-flow interpretation limits.
2. Update `docs/runbooks/developer-maintenance.md` with endpoint contract, payload fields, flow definitions, provider capability notes, and focused validation commands.
3. Update `README.md` Phase 2 feature status based on the final implementation state.
4. Record completed validation in this file before archival.

## Validation Commands

- `python -m pytest tests/services/test_hot_sectors_service.py tests/api/test_sectors_api.py`
- `npx vitest run "apps/web/app/api/hot-sectors/route.test.ts" "apps/web/components/hot-sectors.test.tsx" "apps/web/app/[locale]/page.test.tsx"`
- `npm run test:web`
- `git diff --check`

## Completed Validation

- Backend service/API focused tests passed: `python -m pytest tests/services/test_hot_sectors_service.py tests/api/test_sectors_api.py` → `10 passed`.
- Frontend focused tests passed: `npx vitest run "apps/web/app/api/hot-sectors/route.test.ts" "apps/web/components/hot-sectors.test.tsx" "apps/web/app/[locale]/page.test.tsx" --reporter=dot` → `3 passed`, `12 passed`.
- Component-specific rerun passed after null/unknown flow assertions were aligned with localized unavailable text: `npx vitest run "apps/web/components/hot-sectors.test.tsx" --reporter=verbose` → `5 passed`.
- Full frontend suite passed: `npm run test:web` → `29 passed`, `92 passed`.
- Whitespace check passed: `git diff --check` → exit code `0` with CRLF conversion warnings only.
- IDE lint check passed for edited backend/frontend hot-sector files → `0` diagnostics.
- Documentation updated in `README.md`, `docs/manual/user-guide.md`, and `docs/runbooks/developer-maintenance.md` to describe the provider-backed MVP, data modes, flow definitions, provider capabilities, and professional benchmark gaps.

## Risk Controls

- Do not mark static fixtures, demo rows, or stale/unverified values as live verified fund-flow data.
- Keep `/sectors/hot` backward-compatible for the dashboard and existing tests.
- Keep `limit` validation at `1..10`.
- Keep provider failures as typed unavailable/degraded payloads rather than 500s.
- Do not commit unrelated `apps/web/app/api/recommendations/route.ts` line-ending noise.
