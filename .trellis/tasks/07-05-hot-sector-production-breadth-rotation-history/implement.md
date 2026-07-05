# Hot Sector Production Breadth and Rotation History - Implementation Plan

## Execution Order

1. Re-read the hot-sector service, API router, frontend proxy, frontend component, tests, and documentation immediately before editing.
2. Confirm current `/sectors/hot` response shape and preserve backward compatibility.
3. Add or refine backend value objects / typed dictionaries for optional breadth, contribution, taxonomy, capability, and history metadata.
4. Extend service normalization so verified provider fields and unavailable sections are represented explicitly.
5. Keep static fixtures and unavailable providers clearly marked as non-production data.
6. Add deterministic backend tests for:
   - breadth metadata when constituent data is available;
   - unavailable breadth/history sections when provider support is absent;
   - mock/static fixture responses remaining `degraded + mock`;
   - diagnostic sanitization.
7. Extend the Next.js hot-sector proxy only if the upstream payload contract requires additive typing or cache/header updates.
8. Update `HotSectors` to progressively render breadth, contribution, taxonomy, and rotation/history metadata when present.
9. Add or update focused frontend tests for new visible states and unavailable/degraded notices.
10. Update user and developer documentation with provider capability, flow definition, verification, and limitation notes.
11. Run focused backend and frontend validation.
12. Decide whether rotation persistence is small enough for this task. If not, record a follow-up instead of adding a half-implemented storage layer.

## Files To Inspect Before Editing

- `packages/services/hot_sectors.py`
- `apps/api/routers/sectors.py`
- `apps/web/app/api/hot-sectors/route.ts`
- `apps/web/components/hot-sectors.tsx`
- `tests/services/test_hot_sectors_service.py`
- Any existing hot-sector API, proxy, page, or component tests discovered by search.
- `docs/manual/user-guide.md`
- `docs/runbooks/developer-maintenance.md`
- `README.md` if the feature status table needs a wording update.

## Backend Checklist

- [x] Identify existing payload classes and status/data-mode semantics.
- [x] Add additive optional fields without breaking existing callers.
- [x] Represent provider capabilities separately from actual data values.
- [x] Ensure unavailable breadth/history/contribution data is not encoded as zero.
- [x] Ensure provider exceptions produce safe diagnostics with no secret leakage.
- [x] Keep mock/static fixture paths visibly degraded and mock-labeled.
- [x] Add focused service/API tests for supported, partial, unavailable, and mock states.

## Frontend Checklist

- [x] Update local payload types for optional fields.
- [x] Render breadth metrics only when present.
- [x] Render contribution leaders and laggards only when present.
- [x] Render history/rotation metadata only when backed by explicit snapshot fields.
- [x] Preserve existing empty, degraded, unavailable, and mock notices.
- [x] Add focused component/proxy/page tests for new states.
- [x] Keep all user-visible static strings in locale files if the component currently follows i18n message patterns.

## Documentation Checklist

- [x] Explain provider verification states.
- [x] Explain `live`, `delayed`, `demo`, `mock`, and `none` data modes.
- [x] Explain breadth and contribution metrics, including unavailable-state semantics.
- [x] Explain that static fixtures and degraded mock data are not market signals.
- [x] Add validation commands and provider-readiness guidance for maintainers.

## Validation Commands

Start with focused deterministic checks:

```powershell
python -m pytest tests/services/test_hot_sectors_service.py -q
```

Run any discovered hot-sector API tests, for example:

```powershell
python -m pytest tests/api -q -k "sector or hot"
```

Run focused frontend tests after identifying the exact files:

```powershell
npm run test:web -- apps/web/components/hot-sectors.test.tsx
```

Run broader checks before completion when practical:

```powershell
python -m pytest tests -q
npm run test:web
```

Optional live smoke checks must remain opt-in and should not be required for deterministic CI:

```powershell
python scripts/provider_readiness.py --provider akshare --market CN --symbol 600519 --real-network
```

## Rollback Points

- After backend contract changes and focused backend tests.
- After frontend rendering updates and focused frontend tests.
- After documentation updates.
- Before any schema migration or persistent rotation-history work.

## Out-Of-Scope Unless Explicitly Approved

- Full production Level-2 order-flow integration.
- Paid provider entitlement workflow.
- Large persistent time-series storage or scheduler changes for sector snapshots.
- A full Eastmoney/Tonghuashun parity sector terminal.

## Completed Implementation Notes

- Backend hot-sector service now returns additive item-level `breadth`, `constituent_contribution`, `taxonomy`, and `history` sections.
- Top-level payloads now include provider capability metadata for ranking, fund flow, constituents, breadth, contribution, rotation history, and taxonomy.
- Unknown providers and provider exceptions still return typed `unavailable` payloads and do not leak secret-like exception content.
- Static fixture fallback remains `degraded + mock`, and breadth/contribution derived from that path are marked as mock rather than production signal.
- Frontend `HotSectors` renders breadth, positive/negative contributors, taxonomy version, and explicit unavailable rotation-history copy.
- User/developer docs and README now describe the new metadata and current production limitations.

## Completed Validation

- `python -m pytest tests/services/test_hot_sectors_service.py tests/api/test_sectors_api.py -q` -> `10 passed`
- `npm run test:web -- apps/web/app/api/hot-sectors/route.test.ts apps/web/components/hot-sectors.test.tsx` -> `10 passed`
