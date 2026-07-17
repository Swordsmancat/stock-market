# Stored market movers implementation plan

## 1. Backend

- Add `packages/services/market_movers.py` with validation, coherent date and
  dominant cohort selection, exact-date joins, deterministic ranking, and
  explicit no-data payloads.
- Add `apps/api/routers/market_movers.py` and register it in `apps/api/main.py`.
- Add focused service and API tests covering every PRD invariant.

## 2. Frontend

- Run the UI design-system searches required by the project UI skill.
- Add a decoder/formatter module with focused tests.
- Add `/[locale]/market-movers/page.tsx` and a page test for controls, links,
  stored provenance, empty state, and backend failure.
- Add a desktop-only navigation item, breadcrumb support, and locale messages;
  update navigation tests while preserving the current mobile item count.

## 3. Validation

```powershell
python -m ruff check packages/services/market_movers.py apps/api/routers/market_movers.py tests/services/test_market_movers_service.py tests/api/test_market_movers_api.py
pytest -q tests/services/test_market_movers_service.py tests/api/test_market_movers_api.py
npm run test:web -- --run apps/web/lib/market-movers.test.ts apps/web/app/[locale]/market-movers/page.test.tsx apps/web/components/navigation-items.test.ts apps/web/components/sidebar-navigation.test.tsx
npm run typecheck --workspace apps/web
python -m json.tool apps/web/messages/zh.json
python -m json.tool apps/web/messages/en.json
python ./.trellis/scripts/task.py validate 07-17-market-movers-ranking
git diff --check -- packages/services/market_movers.py apps/api/routers/market_movers.py apps/api/main.py tests/services/test_market_movers_service.py tests/api/test_market_movers_api.py apps/web/lib/market-movers.ts apps/web/lib/market-movers.test.ts apps/web/app/[locale]/market-movers apps/web/components/navigation-items.ts apps/web/components/navigation-items.test.ts apps/web/components/sidebar-navigation.test.tsx apps/web/components/breadcrumbs.tsx apps/web/messages/zh.json apps/web/messages/en.json .trellis/tasks/07-17-market-movers-ranking .trellis/tasks/07-17-reference-modules-integration
```

## Rollback points

- Backend and frontend are additive and can be removed independently before
  navigation exposure.
- Do not modify daily-bar ingestion, existing provider automation, migrations,
  homepage behavior, or unrelated dirty files.
