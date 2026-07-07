# Implementation Plan

## Scope Decision

This is an inline Codex implementation task. Do not dispatch implement/check subagents. The first implementation slice should be small and end-to-end:

1. Fix currently visible frontend display bugs found by browser inspection.
2. Add homepage followed/favorite macro indicators.
3. Keep macro detail in `/evidence`, with visible wording changed toward Macro Research.
4. Preserve all citation and safety boundaries.

## Pre-Implementation

- Treat these existing dirty files carefully and do not stage unrelated changes unless inspection shows they belong to this task:
  - `apps/web/components/navigation-items.ts`
  - `apps/web/components/navigation-items.test.ts`
  - `packages/services/market_assistant.py`
  - `tests/ai/test_market_assistant.py`
- Load `trellis-before-dev` before editing.
- Read relevant specs:
  - `.trellis/spec/frontend/index.md`
  - `.trellis/spec/frontend/component-guidelines.md`
  - `.trellis/spec/frontend/type-safety.md`
  - `.trellis/spec/frontend/quality-guidelines.md`
  - `.trellis/spec/backend/index.md`
  - `.trellis/spec/backend/assistant-research-citation-contract.md`
  - `.trellis/spec/backend/market-indicator-seed-import-contract.md`

## Ordered Work

### 1. Browser Bug Triage

- Start the web/API dev environment if needed.
- Inspect:
  - `/zh`
  - `/zh/evidence`
  - one `/zh/instruments/<symbol>` route with the Market Assistant card
  - mobile viewport for `/zh` and `/zh/evidence`
- Record concrete symptoms in task notes or PRD if new defects are found.
- Fix only user-visible display bugs in this task.

### 2. Settings Contract For Macro Favorites

- Add `favorite_macro_indicator_codes` to Python platform settings:
  - `packages/services/platform_settings.py`
  - tests under `tests/api/test_settings_api.py` if API payload coverage needs updating.
- Add the same field to frontend settings:
  - `apps/web/lib/platform-settings-store.ts`
  - `apps/web/app/api/settings/route.ts`
  - `apps/web/app/api/platform-settings/route.ts` if it mirrors settings
  - `apps/web/app/[locale]/actions.ts`
- Normalize lists consistently:
  - trim;
  - drop empty codes;
  - de-duplicate preserving order.

### 3. Settings UI Or Low-Friction Editing

- Add a simple settings control for favorite macro indicator codes.
- Preferred first slice: a compact textarea or comma-separated input with helper text and a documented default list.
- If an available-indicator checkbox UI is simpler after inspection, use that instead.
- Keep English and Chinese translations synchronized.

### 4. Homepage Macro Favorites Module

- In `apps/web/app/[locale]/page.tsx`, filter `marketOverviewPayload.macro_indicators?.items` / `valuation_indicators.items` by the favorite codes.
- Add helper functions for:
  - default favorite code list;
  - favorite filtering and fallback;
  - compact status label;
  - indicator value/date/source formatting.
- Ensure the default favorite list includes both `buffett_indicator_us` and `buffett_indicator_cn`, with `buffett_indicator_hk` allowed as a companion when present.
- Place the module near the dashboard brief / market dashboard summary, before lower-priority operational diagnostics.
- Include a link to `/evidence` for full macro research details.
- Keep UI dense and practical: compact cards or table rows, not a large hero.

### 5. Macro Research Detail Wording

- Keep route `/evidence`.
- Update navigation label and page wording toward "Macro Research" / "宏观研究".
- Keep advanced manual tools collapsed and clearly secondary.
- Ensure source capability/status guidance appears as non-citable collection guidance if surfaced.

### 6. Tests

- Update `apps/web/app/[locale]/page.test.tsx` to assert:
  - homepage favorite macro module renders;
  - US and mainland China Buffett Indicator rows are both shown by default when present;
  - available and missing indicator states render;
  - detail link points to `/evidence`;
  - dashboard citations do not include source capability/readiness IDs.
- Update navigation tests if label/title keys change.
- Update settings tests for `favorite_macro_indicator_codes`.
- Update Evidence Center tests only if wording or ordering changes.

## Validation Commands

Focused checks:

```powershell
npx vitest run "apps/web/app/[locale]/page.test.tsx" "apps/web/app/[locale]/evidence/page.test.tsx" "apps/web/components/navigation-items.test.ts" "apps/web/app/api/settings/route.test.ts" --reporter=dot
pytest tests/api/test_settings_api.py -q
```

Type and broader web checks:

```powershell
npx tsc -p apps/web/tsconfig.json --noEmit
npm run test:web -- --reporter=dot
```

If backend settings helpers change:

```powershell
pytest tests/api/test_settings_api.py tests/services/test_market_dashboard_service.py -q
```

Final checks:

```powershell
git diff --check
python ./.trellis/scripts/task.py validate .trellis/tasks/07-07-frontend-bugs-macro-research-cockpit
```

Browser smoke:

- `/zh` desktop and mobile render without console errors or horizontal overflow.
- `/zh/evidence` desktop and mobile render without console errors or horizontal overflow.
- Homepage shows followed/favorite macro indicators.
- Macro detail link from homepage opens `/zh/evidence`.

## Review Gate Before Start

- User reviews and approves `prd.md`, `design.md`, and `implement.md`.
- Then run:

```powershell
python ./.trellis/scripts/task.py start .trellis/tasks/07-07-frontend-bugs-macro-research-cockpit
```

Implementation begins only after the task is active.

## Rollback Points

- Homepage macro favorites module can be reverted independently.
- Platform settings favorite field is additive and can be ignored by the UI if needed.
- Navigation label changes can be reverted without route changes.
