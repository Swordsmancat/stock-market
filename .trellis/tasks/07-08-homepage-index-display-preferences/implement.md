# 首页核心指数自选展示参数 - Implement

## Ordered Checklist

- [x] Before coding, load `trellis-before-dev` and re-read this task's `prd.md`, `design.md`, `implement.md`, plus relevant frontend specs.
- [x] Add settings contract in `apps/web/lib/platform-settings-store.ts`:
  - `HomeIndexDisplayField`
  - `DEFAULT_FAVORITE_HOME_INDEX_CODES`
  - `DEFAULT_HOME_INDEX_DISPLAY_FIELDS`
  - normalizers for home index codes and display fields
  - public `PlatformSettings` fields
- [x] Update platform settings save flow:
  - `savePlatformSettings` accepts the two new fields
  - `savePlatformSettingsAction` reads form values and forwards them
  - settings API route tests are updated if exact payloads need the new fields
- [x] Add Settings page UI:
  - "Homepage core indices" card near macro favorites
  - textarea for ordered index codes
  - checkbox group for card display fields
  - header metric updated only if it stays readable and useful
- [x] Add translations in `apps/web/messages/en.json` and `apps/web/messages/zh.json`.
- [x] Update homepage index selection:
  - build ordered homepage index rows from configured codes
  - use the same rows for `MarketTicker` and core index cards
  - render explicit unavailable card for configured codes missing from payload
  - hide/show card fields according to `home_index_display_fields`
- [x] Preserve curated homepage exclusions:
  - no AI research brief
  - no comparison tool
  - no followed K-line workspace
  - no reports, technical indicators, or fundamentals blocks
- [x] Update focused tests:
  - platform-settings normalization
  - settings save action
  - settings API route exact payloads if needed
  - homepage configured order/fallback/missing-code behavior
  - homepage no-deep-module regression
- [x] Run validation commands.
- [x] Update `.trellis/spec/frontend/` only if implementation discovers a reusable convention beyond the existing curated homepage rule. No new spec convention was needed; the existing curated homepage rule covers this work.

## Implementation Notes

- Added `favorite_home_index_codes` and `home_index_display_fields` to the platform settings contract with default values and normalization helpers.
- Added a Settings page "Homepage Core Indices" card with a code-order textarea and display-field checkboxes.
- Wired `savePlatformSettingsAction`, `/api/settings`, and `/api/platform-settings` to carry the new fields.
- Updated the homepage so `MarketTicker` and core index cards share the same configured index order.
- Added explicit unavailable rendering when a configured index code is not present in the market overview payload.
- Added card-field controls for latest close, percent change, freshness, as-of date, region, and provider/source.
- Kept deep modules off the homepage; no AI brief, comparison tool, K-line workspace, reports, technical indicators, or fundamentals blocks were reintroduced.

## Validation Evidence

- `node -e "JSON.parse(require('fs').readFileSync('apps/web/messages/en.json','utf8')); JSON.parse(require('fs').readFileSync('apps/web/messages/zh.json','utf8')); console.log('messages ok')"` passed.
- Focused Vitest passed: `npx vitest run "apps/web/lib/platform-settings-store.test.ts" "apps/web/app/[locale]/actions.test.ts" "apps/web/app/api/settings/route.test.ts" "apps/web/app/[locale]/settings/page.test.tsx" "apps/web/app/[locale]/page.test.tsx" --reporter=dot` passed 5 files / 19 tests.
- TypeScript passed: `npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0`.
- Full frontend tests passed: `npm run test:web -- --reporter=dot` passed 52 files / 166 tests. The hot-sectors `network down` stderr is from an existing test that intentionally exercises the degraded branch.
- `git diff --check` passed with Git CRLF warnings only.

## Validation Commands

```powershell
npx vitest run "apps/web/lib/platform-settings-store.test.ts" "apps/web/app/[locale]/actions.test.ts" "apps/web/app/api/settings/route.test.ts" "apps/web/app/[locale]/settings/page.test.tsx" "apps/web/app/[locale]/page.test.tsx" --reporter=dot
npm run test:web -- --reporter=dot
npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0
git diff --check
```

## Risky Files And Rollback Points

- `apps/web/lib/platform-settings-store.ts`: broad settings contract impact; verify old files without the new keys still load.
- `apps/web/app/[locale]/actions.ts`: server action must preserve existing sensitive setting behavior.
- `apps/web/app/[locale]/settings/page.tsx`: large form; ensure all existing inputs still submit.
- `apps/web/app/[locale]/page.tsx`: homepage information architecture must remain curated and responsive.
- `apps/web/messages/en.json`, `apps/web/messages/zh.json`: avoid raw JSON/brace examples in translated strings.
- `data/platform_settings.json`: do not commit real secret churn; implementation should not rewrite the user's local secrets during tests.

## Pre-Implementation Notes

- Prefer extracting small pure helpers in `page.tsx` or `platform-settings-store.ts` when needed for testability.
- Keep field controls server-rendered form inputs; no client component is required for the MVP.
- Use checkboxes with the same `name="home_index_display_fields"` repeated for multiple selected values; `FormData.getAll()` can read them in the Server Action.
- If exact settings API tests become noisy, assert behaviorally on the new fields plus existing sensitive-field masking rather than snapshot-like whole payloads.

## Follow-Up Checks Before `task.py start`

- [x] `prd.md`, `design.md`, and `implement.md` reviewed.
- [x] User confirmed the recommended MVP scope on 2026-07-08:
  - textarea ordering for index codes
  - checkbox field selection
  - no drag-and-drop
  - no account sync
  - no new backend market-data API
