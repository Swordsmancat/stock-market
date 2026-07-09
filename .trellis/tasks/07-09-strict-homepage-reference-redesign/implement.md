# Strict homepage reference redesign implementation plan

## Checklist

- [x] Activate the Trellis task after user approval with `python ./.trellis/scripts/task.py start 07-09-strict-homepage-reference-redesign`.
- [x] Run `trellis-before-dev` context checks for frontend package and confirm relevant specs are loaded.
- [x] Refactor `apps/web/app/[locale]/page.tsx`:
  - Remove the large `FinancialDashboardHero` from the normal homepage path.
  - Add homepage-local terminal panel helpers for tables, charts, gauge, ticker groups, and provider strip.
  - Preserve existing data fetches and settings-driven index preference behavior.
  - Render multi-row latest news.
  - Render compact macro, hot-sector, overview, fund-flow, AI sentiment, and provider panels.
- [x] Update `apps/web/messages/en.json` and `apps/web/messages/zh.json` for new visible labels.
- [x] Update `apps/web/app/[locale]/page.test.tsx`:
  - Assert the new reference panel titles render.
  - Assert multiple news rows render.
  - Assert provider readiness still includes ready and needs-key states.
  - Keep existing tests for index order, missing index, and absence of deep modules.
- [x] Run focused validation.
- [x] If focused validation passes, run broader frontend validation if time permits.
- [x] Update frontend spec if this introduces a durable convention beyond the existing terminal homepage convention. Existing `Terminal Dashboard Homepage` guidance already covers this slice, so no spec edit was needed.
- [ ] Commit changes after checks pass.

## Validation Run

- `npm run test:web -- "apps/web/app/[locale]/page.test.tsx" "apps/web/components/market-ticker.test.tsx" --reporter=dot` passed.
- `npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0` passed.
- `git diff --check` passed. Git only reported line-ending normalization warnings.
- Visual check passed with system Chrome at `http://127.0.0.1:3000/en`: desktop 1440x900 and mobile 390x844 had no horizontal overflow, all target terminal panel titles were present, and desktop first viewport included the lower panels plus news source status cards.

## Validation Commands

```powershell
npm run test:web -- apps/web/app/[locale]/page.test.tsx apps/web/components/market-ticker.test.tsx --reporter=dot
git diff --check
```

Optional broader checks:

```powershell
npm run test:web -- --reporter=dot
npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0
```

Visual check:

- Use the local dev server if already running, or start one if needed.
- Capture desktop 1440x900 and mobile screenshots with Playwright/system Chrome.
- Check that the first viewport has no horizontal overflow and the desktop grid geometry matches the reference.

## Risk Points

- `apps/web/app/[locale]/page.tsx` is already large. Keep edits scoped and avoid unrelated fetch contract changes.
- Tests contain many assertions from older homepage scopes. Update them to current behavior without weakening absence checks for deep modules.
- Generated chart/gauge SVGs must render non-empty paths/bars with fixture data.
- Chinese and English translations must stay aligned.
