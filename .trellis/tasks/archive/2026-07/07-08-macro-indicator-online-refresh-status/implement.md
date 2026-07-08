# Macro indicator online refresh status UI implementation plan

## Checklist

- [x] Load `trellis-before-dev` before code edits.
- [x] Read relevant backend and frontend specs:
  - `.trellis/spec/backend/index.md`
  - `.trellis/spec/backend/market-indicator-seed-import-contract.md`
  - `.trellis/spec/frontend/index.md`
  - frontend component/quality/type-safety guidelines.
- [x] Add FastAPI request/response models and endpoints in `apps/api/routers/market_indicators.py`.
- [x] Map service result dataclasses to response payloads.
- [x] Handle sanitized FRED/World Bank/provider/validation errors.
- [x] Clear market-overview cache only after successful non-dry-run refresh.
- [x] Add backend API tests in `tests/api/test_market_indicators_api.py`.
- [x] Add Next.js proxy routes for FRED and World Bank official refresh.
- [x] Add proxy route tests.
- [x] Add a client refresh-action component for Macro Research.
- [x] Update `apps/web/app/[locale]/evidence/page.tsx` to render controls inside the existing official refresh panels.
- [x] Update English and Chinese messages.
- [x] Update Evidence Center page/component tests.
- [x] Run focused backend tests.
- [x] Run focused frontend/proxy tests.
- [x] Run TypeScript and full web tests.
- [x] Run `git diff --check`.
- [x] Browser smoke Macro Research desktop/mobile.
- [x] Validate Trellis task.

## Suggested Validation Commands

```powershell
pytest tests/api/test_market_indicators_api.py tests/services/test_market_indicators_fred_refresh.py tests/services/test_market_indicators_world_bank_refresh.py tests/scripts/test_refresh_fred_macro_indicators.py tests/scripts/test_refresh_world_bank_macro_indicators.py -q
npx vitest run "apps/web/app/[locale]/evidence/page.test.tsx" "apps/web/app/api/market-indicators/official-refresh/fred/route.test.ts" "apps/web/app/api/market-indicators/official-refresh/world-bank/route.test.ts" --reporter=dot
npx tsc -p apps/web/tsconfig.json --noEmit
npm run test:web -- --reporter=dot
git diff --check
python ./.trellis/scripts/task.py validate .trellis/tasks/07-08-macro-indicator-online-refresh-status
```

## Risky Files

- `apps/api/routers/market_indicators.py`: mutation endpoints must preserve seed preview/import behavior.
- `packages/services/market_indicators.py`: avoid changing provider normalization unless tests prove a service bug.
- `apps/web/app/[locale]/evidence/page.tsx`: large server page; keep changes around the existing official refresh panel.
- `apps/web/messages/en.json` / `apps/web/messages/zh.json`: keep JSON valid and update together.

## Rollback Points

- Backend endpoint additions can be reverted independently from existing scripts/services.
- Next.js proxy additions are isolated under `/api/market-indicators/official-refresh/*`.
- UI controls can be removed while leaving command/runbook guidance intact.
