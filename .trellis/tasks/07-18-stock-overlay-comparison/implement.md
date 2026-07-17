# Stock and overlay comparison implementation plan

## 1. Backend read contract

- Add `packages/services/market_comparison.py` with bounded validation,
  database-only search, exact identity resolution, coherent per-stock cohort
  selection, shared-date alignment, finite-number serialization, and explicit
  state payloads.
- Add and register `apps/api/routers/market_comparison.py`.
- Add focused service/API tests for every PRD invariant and prove provider/seed
  code is never called.

## 2. Comparison utilities and page

- Add a shared-date alignment helper and regressions to `comparison-utils`.
- Add `/[locale]/instruments/compare/page.tsx` with URL-owned selected symbols,
  stored search results, add/remove controls, period links, provenance, exact
  detail links, and distinct state branches.
- Reuse `ComparisonTool` for analysis and export; change it only where shared
  alignment or dedicated-workspace ergonomics require.
- Remove automatic comparison series loading from the Instruments page and add
  a localized comparison action.
- Add breadcrumb and both locale catalogs without changing navigation items.

## 3. Validation

```powershell
python -m ruff check packages/services/market_comparison.py apps/api/routers/market_comparison.py tests/services/test_market_comparison_service.py tests/api/test_market_comparison_api.py
pytest -q tests/services/test_market_comparison_service.py tests/api/test_market_comparison_api.py
npm.cmd run test:web -- --run apps/web/lib/comparison-utils.test.ts apps/web/app/[locale]/instruments/compare/page.test.tsx apps/web/app/[locale]/instruments/page.test.tsx apps/web/components/comparison-tool.test.tsx
.\node_modules\.bin\tsc.cmd --noEmit -p apps/web/tsconfig.json
node -e "JSON.parse(require('fs').readFileSync('apps/web/messages/zh.json','utf8')); JSON.parse(require('fs').readFileSync('apps/web/messages/en.json','utf8'))"
python ./.trellis/scripts/task.py validate 07-18-stock-overlay-comparison
git diff --check -- packages/services/market_comparison.py apps/api/routers/market_comparison.py apps/api/main.py tests/services/test_market_comparison_service.py tests/api/test_market_comparison_api.py apps/web/lib/comparison-utils.ts apps/web/lib/comparison-utils.test.ts apps/web/app/[locale]/instruments/compare apps/web/app/[locale]/instruments/page.tsx apps/web/app/[locale]/instruments/page.test.tsx apps/web/components/comparison-tool.tsx apps/web/components/comparison-tool.test.tsx apps/web/components/breadcrumbs.tsx apps/web/messages/zh.json apps/web/messages/en.json .trellis/tasks/07-18-stock-overlay-comparison
```

## Rollback points

- Backend and dedicated page are additive until Instruments ownership moves.
- Keep the old comparison card until the dedicated page tests pass, then remove
  its page-load fetch in one reviewed step.
- Do not modify daily-bar ingestion, provider fallback behavior for other
  consumers, stored rows, the homepage, or navigation item counts.
