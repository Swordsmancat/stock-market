# Frontend bug fixes and macro research cockpit

## Goal

Make the web app feel like a personal macro information and AI research cockpit, not a professional trading terminal or a source-upload workflow. The next implementation slice should first fix currently visible frontend display bugs, then put the user's followed macro indicators on the homepage and keep deeper macro/source details in the existing Evidence Center route.

The user value is fast personal review: open the homepage, see favorite macro and valuation indicators, understand which online/API sources are usable, pick stocks for AI-assisted analysis, and get summarized insights with clear evidence boundaries.

## Confirmed Facts

- The user does not plan to upload local notebooks or local data files as a regular workflow. Data should primarily come from online sources, APIs, and reviewed local observations created by refresh/import flows.
- The user expects macro indicators to be available on the homepage, especially a small set of followed/favorite macro indicators.
- Buffett Indicator is a market-wide valuation indicator, not an individual-stock metric. The homepage should support at least US-market and mainland-China-market Buffett Indicator views; Hong Kong can remain an optional/default-detail companion when data exists.
- The user accepts using the agent's recommendation for deeper macro detail placement.
- The product should not compete with professional trading terminals. It should be a personal information aggregation and AI summary/recommendation tool.
- The existing `07-03-frontend-ui-polish` task is implementation/evidence complete from its own PRD and is archive-ready; this task should not reopen that broad UI-polish scope.
- The homepage already fetches recommendation data through `/recommendations` and renders `SmartRecommendations` (`apps/web/app/[locale]/page.tsx`).
- The homepage already receives `marketOverviewPayload.macro_indicators` / `valuation_indicators` and renders a macro/valuation indicator section lower on the page (`apps/web/app/[locale]/page.tsx`).
- Individual instrument detail already has a `MarketAssistantCard` entry through `apps/web/components/instrument-detail-client.tsx`.
- Evidence Center already renders macro/valuation evidence, dashboard brief narrative, source readiness, saved research briefs, and advanced manual tools (`apps/web/app/[locale]/evidence/page.tsx`).
- Evidence Center already hides manual seed import, Source Notebook, and research follow-up queue under an "Advanced source review tools" details panel.
- Market overview payload types already expose `macro_indicators`, `valuation_indicators`, `dashboard_brief`, `information_sources`, `research_follow_up_queue`, and `information_sources.source_capabilities` (`apps/web/lib/market-overview-payload.ts`).
- Platform settings already persist single-user preferences in `data/platform_settings.json` through frontend and backend settings helpers (`apps/web/lib/platform-settings-store.ts`, `packages/services/platform_settings.py`).
- The China macro source validation task added capability metadata for NBS, PBOC, World Bank China fallback, IMF/global fallback, Trading Economics, and AkShare/Tushare candidates. Capability metadata remains guidance only, not AI-citable evidence.
- Current git status shows four pre-existing modified paths outside this new task's creation: `apps/web/components/navigation-items.ts`, `apps/web/components/navigation-items.test.ts`, `packages/services/market_assistant.py`, and `tests/ai/test_market_assistant.py`. Treat them as existing parallel work unless they become directly relevant after inspection.

## Requirements

### R1. Visible Frontend Bug Triage

- Run the app in a browser and inspect the main personal-research paths before changing layout.
- Capture concrete bugs with route, viewport, and symptom:
  - `/zh` or `/en` dashboard.
  - `/zh/evidence` or `/en/evidence`.
  - at least one instrument detail route with AI assistant.
  - navigation/sidebar or mobile navigation if display issues appear.
- Fix visible rendering bugs that block normal personal use, such as broken text, horizontal overflow, invalid layout nesting, inaccessible controls, missing route labels, or misleading labels.
- Do not treat unrelated backend feature work as a display bug unless it prevents the frontend from rendering.

### R2. Evidence Center Default Experience

- Preserve the existing `/evidence` route for compatibility, but present it as macro/research detail rather than a generic upload/evidence workflow.
- Reframe the default Evidence Center experience around macro indicators, valuation indicators, source readiness, source capability guidance, and AI-generated/saved summaries.
- Keep manual seed import, Source Notebook, and research follow-up queue available but secondary because the user does not expect to upload local notebooks or maintain manual source-note workflows day to day.
- Do not remove the underlying manual/review features in this task; hide, rename, or de-emphasize them unless a specific implementation bug requires removal.
- The default first screen should answer: "What macro/valuation signals do I have, what is missing, and what can AI summarize safely?"

### R2a. Homepage Favorite Macro Indicators

- Add a homepage module for followed/favorite macro indicators near the primary research summary, before lower-priority operational diagnostics.
- The module should show a compact watchlist of selected macro/valuation indicators with value, as-of date, source, status, and a clear no-data/source-gap state.
- Use a sensible default favorite set when the user has not configured favorites yet, prioritizing Buffett Indicator, rates, inflation/liquidity, and China macro context where available.
- The default favorite set should include both `buffett_indicator_us` and `buffett_indicator_cn` so the user can compare US market valuation against mainland China market valuation from the homepage.
- Store or derive favorite macro indicator codes in a way that suits a single-user personal app; the preferred path is platform settings because they already persist display/data preferences.
- Provide a path from the homepage module to the macro detail page for all indicators and source status.

### R3. Macro Source Collection Clarity

- Surface China/global macro source capability status in user-facing UI only as collection guidance.
- Make clear which sources are:
  - already backed by local audited observations;
  - adapter-ready or candidate online/API sources;
  - manual-only or blocked;
  - not AI-citable yet.
- Preserve the boundary that source readiness IDs, seed templates, source capability rows, probe URLs, and follow-up prompts are not citations.

### R4. Stock Selection And AI Analysis Entry

- Make it easy to move from the cockpit to choosing a stock and asking AI for analysis.
- Prefer improving discoverability of existing stock/assistant flows before adding new backend endpoints.
- Keep AI output framed as research summary and risk/context analysis, not direct buy/sell/hold, target price, position sizing, or execution advice.

### R5. Navigation And Naming

- Rename the visible navigation/page wording from generic "Evidence" toward "Macro Research" / "宏观研究" or similar, while preserving the `/evidence` route for this slice.
- Keep route compatibility. Do not introduce `/macro` or `/research` in this task unless implementation shows a clear low-risk redirect-only path.
- Update English and Chinese localization together for user-visible wording.

### R6. Tests And Validation

- Add or update focused frontend tests for changed page behavior, navigation labels, and hidden/secondary advanced tools.
- Run TypeScript and relevant web tests.
- Use browser smoke checks for desktop and mobile after visual/layout changes.
- If backend assistant behavior is touched, run focused assistant tests and preserve citation/safety boundaries.

## Acceptance Criteria

- [ ] A new browser validation pass identifies and fixes the concrete frontend display bugs in the current app paths selected for this task.
- [ ] The homepage shows a compact followed/favorite macro indicator module with clear value/source/as-of/status rendering.
- [ ] The homepage default macro favorites include US and mainland China Buffett Indicator rows when those indicators are present in the payload.
- [ ] The homepage macro module has a no-data/source-gap state and links to deeper macro research details.
- [ ] Evidence Center's default view prioritizes macro/valuation indicators, source readiness, and AI summaries over manual upload/notebook workflows.
- [ ] Manual seed import, Source Notebook, and research follow-up queue remain reachable as advanced/secondary tools, but are not presented as the normal primary workflow.
- [ ] China macro source capability status is visible or discoverable as guidance without becoming AI-citable evidence.
- [ ] The UI provides a clear path from macro research context to selecting a stock and using AI analysis.
- [ ] User-visible labels are localized in both English and Chinese.
- [ ] The visible navigation label no longer makes the primary workflow feel like a local upload/evidence notebook, while the existing `/evidence` route remains compatible.
- [ ] Existing citation boundaries remain intact: source guidance, templates, probe status, and follow-up prompts do not appear as dashboard, saved-brief, or assistant citations.
- [ ] Focused frontend tests and TypeScript checks pass.
- [ ] Browser smoke checks cover desktop and mobile for the changed primary routes.

## Out Of Scope

- Building production NBS/PBOC adapters.
- Building a professional trading terminal, broker workflow, realtime execution system, or Level-2 market-data product.
- Removing existing manual evidence features from backend/storage just because they are secondary for the user's workflow.
- Treating source capability or source readiness guidance as AI evidence.
- Direct buy/sell/hold recommendations, target prices, position sizing, or execution instructions.
- Full drag-and-drop dashboard customization. A compact settings-backed favorite list is enough for this slice.
