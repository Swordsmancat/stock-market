# Entrance page terminal visual alignment implementation plan

## Pre-Implementation

- [ ] Run `task.py validate` after planning artifacts are complete.
- [ ] Ask for review/approval before `task.py start`.
- [ ] Load `trellis-before-dev` after the task is started and before code edits.

## Implementation Checklist

- [ ] Reconfirm clean working tree before editing.
- [ ] Audit repeated card/header/content class patterns across target pages.
- [ ] Decide whether to add a small shared terminal section helper or keep scoped class edits.
- [ ] Align `/instruments` search, health, table, and comparison shell.
- [ ] Align `/instruments/[symbol]` detail sections in `InstrumentDetailClient`.
- [ ] Align `/evidence` top evidence/research/source sections.
- [ ] Align `/settings` form card surfaces without changing input names or server action flow.
- [ ] Align `AiResearchDesk` cards/lists enough for homepage AI sentiment entry continuity.
- [ ] Update tests for changed visible behavior.
- [ ] Run automated checks.
- [ ] Run Chrome visual checks for desktop and tall mobile.

## Validation Commands

```powershell
npm run test:web -- "apps/web/app/[locale]/instruments/page.test.tsx" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx" "apps/web/app/[locale]/evidence/page.test.tsx" "apps/web/app/[locale]/settings/page.test.tsx" "apps/web/app/[locale]/ai-research/page.test.tsx" --reporter=dot
npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0
git diff --check
```

If a touched component has its own focused test, add it to the test command.

## Visual Check Commands

- Use the existing local dev server if available; otherwise start `npm run dev:web`.
- Use system Chrome if Playwright browsers are unavailable:
  - `C:/Program Files/Google/Chrome/Application/chrome.exe`
- Capture desktop and tall mobile screenshots for the changed route set or a representative subset.

## Rollback Points

- Keep changes scoped to frontend class/layout/test/message files.
- Avoid editing shared UI primitives unless the local edits clearly duplicate across several pages.
- If a page needs product decisions beyond visual alignment, stop and split that page into a follow-up task.
