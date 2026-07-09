# InStock Daily Data Enhancement Phase 1 Implementation Plan

## Pre-Implementation

- [x] User confirms the Phase 1 scope and approves implementation start.
- [x] Run `python ./.trellis/scripts/get_context.py --mode phase --step 1.4 --platform codex` before `task.py start`.
- [x] Run `python ./.trellis/scripts/task.py validate .trellis/tasks/07-09-instock-daily-data-enhancement`.
- [x] Start the task with `python ./.trellis/scripts/task.py start .trellis/tasks/07-09-instock-daily-data-enhancement` only after approval.

## Backend

- [x] Extend `packages/services/hot_sectors.py` with explicit `sector_type` and `window` handling for industry/concept fund-flow while preserving current defaults.
- [x] Add focused tests in `tests/services/test_hot_sectors_service.py` for industry, concept, unknown provider, provider failure, and empty provider rows.
- [x] Add or extend API tests for `/sectors/hot` query propagation and backward compatibility.
- [x] Add a new service for individual stock fund-flow and limit-up reasons with fake-provider injection for tests.
- [x] Add a FastAPI router for the new daily data service and wire it in `apps/api/main.py`.
- [x] Add service/API tests for provider success, empty rows, provider exception sanitization, and unsupported provider.

## Frontend

- [x] Add Next.js proxy route(s) for the new backend endpoint(s), following existing `apps/web/app/api/**/route.ts` patterns.
- [x] Add shared TypeScript payload types/normalizers where needed.
- [x] Add a compact terminal-style panel to the selected market/research surface.
- [x] Add localized labels to both `apps/web/messages/en.json` and `apps/web/messages/zh.json`.
- [x] Add focused route/component/page tests for successful rows and degraded/unavailable states.

## Documentation and Specs

- [x] Update `docs/runbooks/instock-analysis-integration.md` with the new implemented slice.
- [x] Add/update a backend spec contract if the new route/service introduces a reusable payload contract.
- [x] Keep citation boundaries explicit: provider-live rows are not assistant citations in this phase.

## Validation

Backend focused checks:

```powershell
pytest tests/services/test_hot_sectors_service.py
pytest tests/api/test_sectors_api.py
pytest tests/services/test_market_daily_data_service.py tests/api/test_market_daily_data_api.py
python -m ruff check packages/services/hot_sectors.py packages/services/market_daily_data.py apps/api/routers/market_daily_data.py tests/services/test_hot_sectors_service.py tests/services/test_market_daily_data_service.py tests/api/test_market_daily_data_api.py
```

Frontend focused checks:

```powershell
npm run test:web -- <focused route/component/page tests>
npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0
```

Final checks:

```powershell
python .\.trellis\scripts\task.py validate .trellis\tasks\07-09-instock-daily-data-enhancement
git diff --check
```

## Rollback Points

- If AkShare limit-up reason support is unavailable in the installed package, keep the endpoint but return an explicit `unavailable` payload and defer provider implementation.
- If frontend integration becomes too large, finish backend API plus route proxy first and leave dashboard panel as the next child task.
- If persistence becomes necessary, stop and re-plan because ORM/Alembic/citation contracts are out of the current MVP scope.
