# Macro data source status and refresh guidance UI implementation plan

## Checklist

- [x] Resolve planning open question: do not persist refresh-run history in this MVP.
- [x] Load `trellis-before-dev` before code edits.
- [x] Read backend and frontend specs:
  - `.trellis/spec/backend/index.md`
  - `.trellis/spec/backend/error-handling.md`
  - `.trellis/spec/backend/quality-guidelines.md`
  - `.trellis/spec/backend/market-indicator-seed-import-contract.md`
  - `.trellis/spec/frontend/index.md`
  - `.trellis/spec/frontend/component-guidelines.md`
  - `.trellis/spec/frontend/state-management.md`
  - `.trellis/spec/frontend/quality-guidelines.md`
  - `.trellis/spec/frontend/type-safety.md`
- [x] Add official macro source status service/projection.
- [x] Add FastAPI route for official macro source status.
- [x] Add backend tests for FRED configured/unconfigured, World Bank no-secret availability, evidence count/latest as-of, and no secret leakage.
- [x] Use server fetch for the status payload; no Next.js proxy is needed because both consumers are server pages.
- [x] Add frontend types for provider source status payload.
- [x] Update Macro Research official refresh panels to show provider status/readiness.
- [x] Update homepage favorite macro cards with source-specific missing-value guidance.
- [x] Update English and Chinese messages.
- [x] Add/update Macro Research page tests.
- [x] Add/update homepage page tests.
- [x] Run focused backend tests.
- [x] Run focused frontend/proxy tests.
- [x] Run `npx tsc -p apps/web/tsconfig.json --noEmit`.
- [x] Run `npm run test:web -- --reporter=dot`.
- [x] Run `git diff --check`.
- [x] Browser smoke `/en/evidence`, `/zh/evidence`, and homepage desktop/mobile.
- [x] Update backend code-spec for official macro source status projection.
- [x] Validate Trellis task.

## Suggested Validation Commands

```powershell
pytest tests/api/test_market_indicators_api.py tests/services/test_market_indicators_service.py tests/services/test_information_sources_service.py tests/api/test_dashboard_api.py -q
npx vitest run "apps/web/app/[locale]/evidence/page.test.tsx" "apps/web/app/[locale]/page.test.tsx" --reporter=dot
npx tsc -p apps/web/tsconfig.json --noEmit
npm run test:web -- --reporter=dot
git diff --check
python ./.trellis/scripts/task.py validate .trellis/tasks/07-08-macro-data-source-status-ui
```

## Risky Files

- `apps/api/routers/market_indicators.py`: new route must not change refresh/seed import behavior.
- `packages/services/market_indicators.py`: keep source status as a projection; do not mutate observations.
- `apps/web/app/[locale]/evidence/page.tsx`: large server page with existing official refresh panels.
- `apps/web/app/[locale]/page.tsx`: homepage layout is dense; keep card guidance concise and responsive.
- `apps/web/messages/en.json` / `apps/web/messages/zh.json`: keep translation keys in sync.

## Rollback Points

- Backend status route can be reverted independently.
- Macro Research status UI can be removed while keeping refresh buttons.
- Homepage missing-value guidance can be reverted without touching backend refresh.
