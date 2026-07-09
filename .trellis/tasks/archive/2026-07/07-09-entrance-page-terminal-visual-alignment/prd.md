# Entrance page terminal visual alignment

## Goal

Make the existing pages reached from the homepage terminal actions feel like the same product as the new dark terminal homepage: dense, dark, bordered, data-first, and visually consistent, without adding new backend contracts or new routed pages.

## Background

- The homepage terminal modules now route users into existing pages via localized "More" actions.
- The current entry targets are:
  - `/instruments`
  - `/instruments/[symbol]`
  - `/evidence`
  - `/settings`
  - `/ai-research`
- These pages mostly already use `FinancialPageHeader`, but their downstream cards, forms, status blocks, and table shells still mix default Card styling, loose spacing, and `rounded-lg` blocks.
- The repo has an active frontend convention for dense terminal pages in `.trellis/spec/frontend/component-guidelines.md`.
- The working tree false-dirty state from backend/service files was cleaned before task creation; this task starts from a clean tree.

## Requirements

- R1: Align the listed entry pages with the homepage terminal visual language: compact sections, subtle borders, dark-friendly surfaces, consistent header bars, and restrained rounded corners.
- R2: Preserve each page's existing information architecture, routes, data fetching, and user workflows.
- R3: Reuse existing primitives (`FinancialPageHeader`, `Card`, `Badge`, `Button`, `Table`, `EmptyState`, `ErrorState`) and add a shared helper only if it meaningfully reduces repeated terminal panel markup across several pages.
- R4: Keep all visible copy localized through the existing message files when new labels are necessary.
- R5: Do not expose provider secrets or alter citation/data trust boundaries while restyling settings, evidence, or research surfaces.
- R6: Keep the changes frontend-only unless implementation discovers a blocking UI contract issue that must be planned separately.
- R7: Add/update focused page/component tests for visible behavior that changes, especially route actions, empty/error states, and localized labels.
- R8: Verify the aligned pages visually in Chrome at desktop and tall mobile sizes.

## MVP Page Scope

- `/instruments`: align search/filter panel, health summary, instrument table container, and comparison tool shell with the terminal visual language.
- `/instruments/[symbol]`: align detail sections for assistant, reports, indicators, fundamentals, news, market depth, intraday, and K-line containers where they currently look detached from the homepage style.
- `/evidence`: align the top research brief/evidence sections and source cards without changing source/citation semantics.
- `/settings`: align provider, news source, model, display, homepage index, and macro favorite settings cards while preserving forms and server action behavior.
- `/ai-research`: align the `AiResearchDesk` shell/cards enough that the homepage AI sentiment "More" destination does not feel like a separate UI system.

## Out of Scope

- Creating a dedicated news sentiment page or sector detail page.
- New market/news/search data endpoints.
- New persisted layout preferences.
- Reworking sidebar/global navigation.
- Changing trading/research boundaries.
- Full design-system token rewrite.

## Acceptance Criteria

- [ ] All MVP target pages retain their current route behavior and data loading.
- [ ] The target pages use consistent terminal-style section surfaces: `rounded-md` or smaller, visible borders, dark-friendly backgrounds, dense headers, and no decorative landing-page layouts.
- [ ] Existing forms, tables, and action buttons remain accessible and keyboard reachable.
- [ ] New visible copy, if any, is present in both English and Chinese locale files.
- [ ] Page tests or component tests cover any changed visible actions/states.
- [ ] TypeScript and focused frontend tests pass.
- [ ] Chrome visual checks cover desktop and tall mobile viewports for the changed route set or a representative subset if the final implementation is split.
