# Improve core information display - Implementation Plan

## Scope

Improve the information hierarchy on the dashboard, instrument detail, instruments list, and reports page without adding new backend contracts.

## Ordered checklist

1. Load Trellis implementation context before code changes.
   - Read frontend specs and cross-layer guide.
   - Confirm current task status and working tree state.
2. Update dashboard derived models in `apps/web/app/[locale]/page.tsx`.
   - Add shared freshness/date/change formatting helpers where local helpers are sufficient.
   - Fetch latest daily bars for the watchlist-first/default-sample health set.
   - Derive fresh/stale/no-data/unavailable counts.
   - Derive primary next action and secondary diagnostic links.
   - Derive daily movement for the primary instrument from recent bars.
3. Reorganize dashboard first screen.
   - Add command-center summary card.
   - Add watchlist/data-health overview card.
   - Add primary instrument daily-story card.
   - Move demo/secondary panels below the primary workspace when necessary.
4. Update instruments page.
   - Reuse existing latest daily bar results to render a visible health summary above the table.
   - Preserve search, filters, table rows, and existing navigation.
5. Update instrument detail page.
   - Add daily absolute/percentage movement from the last two daily bars.
   - Ensure latest volume, date, freshness, source/provider, and chart range are prominent.
   - Add or improve actionable no-data/failure messaging and diagnostic links.
6. Update reports page.
   - Add a small display helper to extract the first markdown heading or meaningful line.
   - Use the extracted insight preview in the table.
7. Update localization.
   - Add all new strings to `apps/web/messages/en.json` and `apps/web/messages/zh.json` together.
8. Update tests.
   - `apps/web/app/[locale]/page.test.tsx`
   - `apps/web/app/[locale]/instruments/page.test.tsx`
   - `apps/web/app/[locale]/instruments/[symbol]/page.test.tsx`
   - `apps/web/app/[locale]/reports/page.test.tsx`
9. Run validation.
   - `npm run test:web -- "apps/web/app/[locale]/page.test.tsx" "apps/web/app/[locale]/instruments/page.test.tsx" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx" "apps/web/app/[locale]/reports/page.test.tsx"`
   - `python ./.trellis/scripts/task.py validate .trellis/tasks/07-03-core-information-display`
   - Read lints for edited frontend files.
10. Commit, push, archive, and continue the Trellis loop according to the user's automation preference.

## Risk points

- Dashboard currently fetches many resources; keep added latest-bar checks bounded to watchlist entries or first 25 instruments.
- Tests may rely on old card text or duplicate values; update assertions to target visible behavior rather than exact layout order.
- Do not imply real-time quote support in labels.
- Do not make portfolio data more prominent because it is demo-oriented.

## Rollback plan

- Revert individual page sections if a focused test reveals a regression.
- Keep backend contracts unchanged so rollback is limited to frontend rendering and localization.

## Review gate before implementation

- PRD has no blocking open questions.
- Design and implementation plan exist.
- Trellis validation passes.
- Task is started before code edits beyond planning artifacts.
