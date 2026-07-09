# Homepage terminal dashboard refactor implementation plan

## Checklist

1. Load implementation context with `trellis-before-dev` before editing production code.
2. Re-read the frontend specs that govern this change:
   - `.trellis/spec/frontend/component-guidelines.md`
   - `.trellis/spec/frontend/state-management.md`
   - `.trellis/spec/frontend/type-safety.md`
   - `.trellis/spec/frontend/quality-guidelines.md`
   - `.trellis/spec/guides/code-reuse-thinking-guide.md`
3. Activate the task with `python ./.trellis/scripts/task.py start 07-09-homepage-terminal-dashboard-refactor` after user approval.
4. Update the app shell:
   - Set first-run theme default to dark in `apps/web/app/[locale]/layout.tsx`.
   - Tune top/sidebar/mobile navigation styling toward dark terminal density while preserving links, search, notifications, language, theme toggle, and account menu.
5. Refactor `MarketTicker`:
   - Keep market filter behavior.
   - Render compact index cards with price, change, percent change, trust title, and a lightweight trend visual.
   - Preserve horizontal overflow behavior without page-level horizontal scroll.
6. Refactor homepage layout in `apps/web/app/[locale]/page.tsx`:
   - Replace the current loose stack with a dense responsive dashboard grid.
   - Keep core index order and display-field settings intact.
   - Present macro favorites, hot sectors, latest news, data health, alerts, latest task run, and primary instrument status as terminal panels.
   - Add the news/provider status strip from `platformSettings.news_search_provider_capabilities`.
   - Keep deep modules absent from homepage.
7. Add or update localized text in `apps/web/messages/en.json` and `apps/web/messages/zh.json`.
8. Update focused tests:
   - Homepage renders terminal dashboard labels and provider strip.
   - Core index preferences still affect ticker and cards.
   - Deep modules are still absent.
   - Optional-data fallback still renders dashboard.
9. Run quality checks.
10. Commit after passing checks and Trellis finish requirements.

## Validation Commands

Run focused checks first:

```powershell
npm run test:web -- apps/web/app/[locale]/page.test.tsx apps/web/components/market-ticker.test.tsx --reporter=dot
```

Then run broader checks:

```powershell
npm run test:web -- --reporter=dot
npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0
git diff --check
```

If browser verification is practical after implementation, start the web app and inspect desktop/mobile viewports for the reference-like terminal layout, non-overlapping text, and horizontal overflow.

## Risky Files and Rollback Points

- `apps/web/app/[locale]/page.tsx` is large and data-heavy. Keep data-fetching helpers stable and change rendering in small sections.
- `apps/web/components/market-ticker.tsx` is client-side and tested; preserve filter state and labels.
- `apps/web/app/[locale]/layout.tsx` default-theme change is small but user-facing.
- `apps/web/messages/*.json` can break ICU parsing; avoid raw braces in message strings.

Rollback points:

- Revert shell default-theme/styling independently from homepage rendering.
- Revert `MarketTicker` independently if client interaction tests fail.
- Remove provider strip independently because it is read-only.
