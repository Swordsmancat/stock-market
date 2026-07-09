# Homepage terminal panel actions and layout polish

## Goal

Polish the existing strict terminal-style homepage so every visible module has a clear "More" path, the macro watch panel exposes "Add custom indicator", and the three center panels keep a fixed, professionally arranged layout at the required desktop and mobile visual-check sizes.

## Background

- The homepage already uses a curated terminal cockpit in `apps/web/app/[locale]/page.tsx`.
- `TerminalPanel` already accepts an `action` slot around `apps/web/app/[locale]/page.tsx:710`, but most modules do not populate it.
- `MacroIndicatorsPanel`, `HotSectorTablePanel`, and `LatestNewsSentimentPanel` already have fixed `xl:h-[15.5rem]` shells around `apps/web/app/[locale]/page.tsx:936`, `apps/web/app/[locale]/page.tsx:999`, and `apps/web/app/[locale]/page.tsx:1059`; their internal content still needs stable header/body sizing.
- Visible homepage copy lives in both `apps/web/messages/en.json` and `apps/web/messages/zh.json`.
- The homepage must remain a compact dashboard. Deep research, K-line, reports, technical indicators, fundamentals, and trading/execution workflows stay off the homepage.

## Requirements

- R1: Add a localized "More" action to every homepage module that is visible in the terminal cockpit.
- R2: Keep "More" actions as real links to existing routes, without adding new pages in this slice.
- R3: Add a localized "Add custom indicator" action to the macro indicators panel.
- R4: Preserve the existing provider secrecy rule: provider status may show readiness metadata, never raw API keys.
- R5: Fix the three middle panels, Macro indicators, Hot sectors, and Latest news sentiment, to the same stable height and make their internal content fit that height at both requested Chrome check sizes.
- R6: On narrow/mobile viewports, the same panels may stack vertically, but each panel must keep the same fixed shell height, stable internal header/body layout, and no horizontal overflow.
- R7: Keep all new visible text localized in English and Chinese message files.
- R8: Add or update page tests so the new actions, routes, and core empty states are covered.

## Module Action Targets

- Market band: "More" opens `/instruments`; existing edit/add settings actions remain available.
- Macro indicators: "More" opens `/evidence`; "Add custom indicator" opens `/settings#favorite_macro_indicator_codes`.
- Hot sectors: "More" opens `/instruments` because there is no sector route in the current app tree.
- Latest news sentiment: "More" opens the current primary instrument detail page, `/instruments/{primaryInstrument.symbol}`, where stored news is already shown.
- Market overview: "More" opens `/instruments`.
- Fund flow: "More" opens `/instruments`.
- AI market sentiment: "More" opens `/ai-research`.
- News source status: "More" opens `/settings`; the existing provider settings action can be converted into or paired with the localized module action.

## Acceptance Criteria

- [ ] Every homepage module renders a localized "More" action with a real href.
- [ ] The macro indicators panel renders a localized "Add custom indicator" action linking to `/settings#favorite_macro_indicator_codes`.
- [ ] The middle three panels have equal fixed height in the desktop and mobile visual checks, and internally separate header/table/list/empty-state regions without clipped headers or overlapping text.
- [ ] The middle panel content is intentionally constrained: long rows truncate or line-clamp inside the panel instead of resizing it.
- [ ] The homepage remains usable when macro, sector, or news data is empty.
- [ ] English and Chinese locale files stay aligned for all new strings.
- [ ] Page tests cover the new action labels and hrefs.
- [ ] Chrome visual checks are performed at desktop `1920x1080` and mobile `1080x1920`.
- [ ] Validation includes the focused homepage test, TypeScript check, and `git diff --check`.

## Out of Scope

- New sector/news/macro detail routes.
- Drag-and-drop homepage customization.
- Persisting new homepage layout preferences.
- Backend data model changes.
- Automatic trading or execution workflows.
