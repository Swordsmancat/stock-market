# Homepage macro favorites and AI research entry

## Goal

Make the homepage work as the user's personal macro-and-AI research starting point: favorite macro indicators stay visible on the dashboard, and the path from macro context to stock selection and AI-assisted research is obvious.

This is an incremental task. The repository already has a first implementation of homepage macro favorites, platform-level favorite macro indicator settings, the Macro Research page at the existing `/evidence` route, and the AI Research Desk at `/ai-research`. This task should verify those pieces in-browser, fix visible frontend bugs, and improve the homepage entry into AI research without adding professional trading-terminal behavior.

## Confirmed Facts

- Current Trellis state has no active task before this task was created.
- Existing dirty files outside this task are `packages/services/market_assistant.py` and `tests/ai/test_market_assistant.py`; they are pre-existing parallel work and must not be reverted or included unless they become directly necessary.
- The homepage already builds favorite macro rows from `marketOverviewPayload.macro_indicators` / `valuation_indicators` and `platformSettings.favorite_macro_indicator_codes` in `apps/web/app/[locale]/page.tsx`.
- The homepage favorite macro module already links to `/evidence` for macro details and `/settings` for editing favorites.
- Default favorite macro indicator support already exists through `DEFAULT_FAVORITE_MACRO_INDICATOR_CODES` and persisted platform settings.
- The Macro Research route keeps compatibility with `/evidence` and already prioritizes macro indicators, dashboard brief, source readiness, saved research briefs, and official refresh guidance.
- The AI Research Desk route exists at `/ai-research` and composes watchlist, followed instruments, recommendations, macro context, diagnostics, and `MarketAssistantCard`.
- Navigation labels already show "Macro Research" / "宏观研究" for the existing `/evidence` route and "AI Research" / "AI 研究" for `/ai-research`.
- `SmartRecommendations` currently contains hardcoded Chinese UI copy. This is visible on the English homepage and makes the personal research dashboard feel inconsistent.
- The product direction remains personal information aggregation and AI research assistance, not direct buy/sell/hold recommendations, price targets, position sizing, broker flows, or realtime trading-terminal competition.

## Requirements

### R1. Browser Validation And Bug Capture

- Run browser smoke checks for the main changed routes before finalizing:
  - `/en`
  - `/zh`
  - `/en/ai-research` or `/zh/ai-research`
- Capture and fix visible frontend bugs that block normal personal use in this slice, especially localization mismatches, missing/weak research entry points, horizontal overflow, and confusing labels.
- Do not include unrelated backend/test dirty files unless implementation directly requires them.

### R2. Homepage AI Research Entry

- Add a clear homepage path into `/ai-research` near the first-screen research summary and/or the favorite macro indicator module.
- The entry should explain, through localized button/label text, that AI Research is for research summaries, macro context, risk/data-gap review, and follow-up questions.
- Keep route compatibility. Do not introduce a new macro route in this task.

### R3. Localized Recommendation Card

- Remove hardcoded Chinese UI copy from `SmartRecommendations`.
- Localize card title, description, empty state, diagnostics heading, confidence label, safety/disclaimer text, and signal-type labels in English and Chinese.
- Recommendation `title` and `reason` remain backend data and should not be translated by the frontend.

### R4. Macro Favorites Stay Focused

- Preserve the current homepage favorite macro indicator behavior:
  - value/source/as-of/status rendering;
  - no-data/source-gap state;
  - default favorites including US and mainland China Buffett Indicator when present;
  - links to Macro Research and Settings.
- If adding an AI Research entry inside this module, keep it secondary to the indicator data and avoid crowding mobile layouts.

### R5. Safety And Citation Boundaries

- Keep AI copy framed as research assistance only.
- Do not add direct buy/sell/hold wording, target prices, position sizing, or execution instructions.
- Do not turn source capabilities, seed templates, probe URLs, or collection guidance into AI-citable evidence.

### R6. Tests And Validation

- Update focused frontend tests for the changed homepage links and localized recommendation copy.
- Run focused tests, TypeScript, and the relevant web test suite.
- Run `git diff --check`.
- Validate the Trellis task before activation/finish.

## Acceptance Criteria

- [x] Homepage has an obvious localized link to `/ai-research` from the first-screen research area or favorite macro indicator module.
- [x] `SmartRecommendations` no longer renders hardcoded Chinese UI shell copy on the English homepage.
- [x] Chinese recommendation UI remains natural on the Chinese homepage.
- [x] Existing recommendation titles/reasons remain data-driven and are not machine-translated by the frontend.
- [x] Favorite macro indicators keep value/source/as-of/status rendering and source-gap behavior.
- [x] US and mainland China Buffett Indicator remain supported as default favorite rows when present in the market overview payload.
- [x] `/evidence` remains the Macro Research detail route; no route compatibility break is introduced.
- [x] AI and recommendation copy stays research-only and avoids direct trading instructions.
- [x] Existing citation boundaries remain intact.
- [x] Focused frontend tests and TypeScript checks pass.
- [x] Browser smoke checks cover desktop and mobile for changed primary routes.

## Out Of Scope

- Production NBS/PBOC adapters, new paid market-data integrations, or scheduled macro refresh jobs.
- Full drag-and-drop dashboard customization.
- Removing existing Source Notebook, seed import, or research follow-up infrastructure.
- Professional trading-terminal features, broker workflows, realtime execution, or Level-2 data.
- Direct investment advice, buy/sell/hold calls, price targets, position sizing, or execution instructions.

## Open Questions

- None blocking. Recommended implementation scope is frontend-only unless browser validation reveals a bug requiring a deeper fix.
