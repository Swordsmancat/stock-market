# Homepage macro favorites and AI research entry implementation plan

## Checklist

- [x] Load frontend pre-development context with `trellis-before-dev` before editing code.
- [x] Update `SmartRecommendations` to accept localized shell labels or otherwise remove hardcoded Chinese UI copy.
- [x] Add English and Chinese messages for recommendation shell labels and homepage AI Research entry copy.
- [x] Add a clear `/ai-research` link on the homepage near the dashboard brief/hero and, if layout allows, the favorite macro module.
- [x] Update focused tests:
  - `apps/web/components/smart-recommendations.test.tsx`
  - `apps/web/app/[locale]/page.test.tsx`
  - navigation tests only if navigation labels change.
- [x] Run focused frontend tests.
- [x] Run `npx tsc -p apps/web/tsconfig.json --noEmit`.
- [x] Run `npm run test:web -- --reporter=dot` if focused tests are stable.
- [x] Run `git diff --check`.
- [x] Browser smoke `/en`, `/zh`, and `/en/ai-research` or `/zh/ai-research` at desktop and mobile widths.
- [x] Validate Trellis task.

## Implementation Notes

- `SmartRecommendations` now receives serialized localized labels from the homepage server component instead of embedding Chinese UI shell copy in the client component.
- The homepage hero includes an `Open AI research` / `打开 AI 研究` action, and the AI research brief area explains that the desk combines stocks, macro context, technical signals, source gaps, and follow-up questions for research assistance only.
- Recommendation titles and reasons remain backend data and are not translated by the frontend.
- No backend API, service, storage, or assistant citation contract changed in this slice.

## Validation Results

- `node -e "JSON.parse(require('fs').readFileSync('apps/web/messages/en.json','utf8')); JSON.parse(require('fs').readFileSync('apps/web/messages/zh.json','utf8')); console.log('messages ok')"` passed.
- `npx vitest run "apps/web/components/smart-recommendations.test.tsx" "apps/web/app/[locale]/page.test.tsx" --reporter=dot` passed: 2 files, 4 tests.
- `npx tsc -p apps/web/tsconfig.json --noEmit` passed.
- `npm run test:web -- --reporter=dot` passed: 47 files, 150 tests. The only stderr was the existing hot-sector test's intentional mocked network-down log.
- `git diff --check` passed, with only Git CRLF normalization warnings.
- Browser smoke passed on the existing Next dev server at `http://localhost:3000`:
  - `/en` and `/zh` at `1440x900` and `390x844` showed localized AI Research links, localized recommendation shell text, Macro Research links, no horizontal overflow, and no runtime-error text.
  - `/en/ai-research` at `1440x900` and `390x844` rendered `AI Research Desk` and the research-only safety boundary, with no horizontal overflow or runtime-error text.
- `python ./.trellis/scripts/task.py validate .trellis/tasks/07-07-homepage-macro-favorites-ai-entry` passed.

## Validation Commands

```powershell
npx vitest run "apps/web/components/smart-recommendations.test.tsx" "apps/web/app/[locale]/page.test.tsx" --reporter=dot
npx tsc -p apps/web/tsconfig.json --noEmit
npm run test:web -- --reporter=dot
git diff --check
python ./.trellis/scripts/task.py validate .trellis/tasks/07-07-homepage-macro-favorites-ai-entry
```

## Risky Files

- `apps/web/app/[locale]/page.tsx`: large server page; keep edits narrowly scoped to actions/props/tests.
- `apps/web/components/smart-recommendations.tsx`: client component with existing tests; avoid changing recommendation item contract.
- `apps/web/messages/en.json` and `apps/web/messages/zh.json`: keep JSON valid and update together.

## Rollback Points

- If localized `SmartRecommendations` creates test/provider churn, switch to explicit label props with defaults.
- If the favorite macro header becomes crowded on mobile, keep only the hero-level `/ai-research` entry and leave macro card links unchanged.
- If browser smoke reveals unrelated display bugs, document them as follow-up unless they block the changed routes.
