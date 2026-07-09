# InStock Dragon Tiger and Block Trades MVP Implementation Plan

## Planning Gate

- [x] User confirms the MVP placement and persistence boundary.
- [x] Run `python ./.trellis/scripts/task.py validate .trellis/tasks/07-09-instock-dragon-tiger-block-trades`.
- [x] Run `python ./.trellis/scripts/get_context.py --mode phase --step 1.4 --platform codex`.
- [x] Start the task with `python ./.trellis/scripts/task.py start .trellis/tasks/07-09-instock-dragon-tiger-block-trades` only after approval.

## Pre-Development Context

- [x] Load `trellis-before-dev` before editing runtime code.
- [x] Read backend specs:
  - `.trellis/spec/backend/index.md`
  - `.trellis/spec/backend/market-daily-data-contract.md`
  - `.trellis/spec/backend/error-handling.md`
  - `.trellis/spec/backend/quality-guidelines.md`
- [x] Read frontend specs:
  - `.trellis/spec/frontend/index.md`
  - `.trellis/spec/frontend/component-guidelines.md`
  - `.trellis/spec/frontend/quality-guidelines.md`
  - `.trellis/spec/frontend/type-safety.md`
- [x] Inspect AkShare function signatures for the selected Dragon Tiger List and
  block-trade provider functions.

## Backend

- [x] Extend `packages/services/market_daily_data.py` with Dragon Tiger List and
  block-trade item dataclasses.
- [x] Extend `MarketDailyDataProvider` and `AkshareMarketDailyDataProvider` with
  fake-testable provider methods.
- [x] Add `get_dragon_tiger_list_payload(...)` and
  `get_block_trades_payload(...)`.
- [x] Add unavailable capability metadata for `dragon_tiger_list` and
  `block_trades`.
- [x] Add FastAPI routes in `apps/api/routers/market_daily_data.py`.
- [x] Add/extend service and API tests for success, empty, invalid date,
  unsupported market/provider, provider exception sanitization, and limit
  validation.

## Frontend

- [x] Add Next route proxies for Dragon Tiger List and block trades.
- [x] Add proxy tests for query normalization, backend forwarding, and failure
  fallback payloads.
- [x] Update `/ai-research` page types/fetches.
- [x] Extend `AiResearchDesk` local payload types and compact market-daily-data
  rendering.
- [x] Add localized labels to `apps/web/messages/en.json` and
  `apps/web/messages/zh.json`.
- [x] Extend AI Research page tests for visible rows and degraded/unavailable
  states.

## Documentation and Spec

- [x] Update `.trellis/spec/backend/market-daily-data-contract.md` with the new
  route signatures, item fields, error matrix, and tests.
- [x] Update `docs/runbooks/instock-analysis-integration.md` with the implemented
  slice and no-trading/no-citation boundary.

## Validation

Focused backend:

```powershell
pytest tests/services/test_market_daily_data_service.py tests/api/test_market_daily_data_api.py
python -m ruff check packages/services/market_daily_data.py apps/api/routers/market_daily_data.py tests/services/test_market_daily_data_service.py tests/api/test_market_daily_data_api.py
```

Focused frontend:

```powershell
npm run test:web -- apps/web/app/api/market-daily-data/dragon-tiger-list/route.test.ts apps/web/app/api/market-daily-data/block-trades/route.test.ts apps/web/app/[locale]/ai-research/page.test.tsx
npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0
```

Final checks:

```powershell
python .\.trellis\scripts\task.py validate .trellis\tasks\07-09-instock-dragon-tiger-block-trades
git diff --check
```

Run broader pytest / Vitest suites if the implementation changes shared helpers
or current daily-data behavior.

## Rollback Points

- If AkShare signatures differ or a function is absent, keep the endpoint and
  return explicit unavailable payloads with provider capability diagnostics.
- If the AI Research Desk panel becomes too crowded, keep backend/proxy routes
  and render only a compact summary plus degraded message, then plan a separate
  market-events page.
- If persistence becomes necessary, stop and re-plan because database/citation
  contracts are out of this MVP scope.
