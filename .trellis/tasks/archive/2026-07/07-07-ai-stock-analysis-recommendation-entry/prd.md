# AI stock analysis and recommendation entry

## Goal

Create a dedicated AI Research Desk page for personal stock research. The page should let the user choose stocks from watchlist items, deterministic recommendation signals, or manual symbol entry, then ask AI for evidence-grounded summaries that combine stock evidence with macro context.

The product direction is a personal information aggregation and AI summary cockpit, not a professional trading terminal. The page should emphasize research questions, citations, risk context, source gaps, and next verification steps rather than buy/sell/hold calls.

## Product Decision

The first MVP surface is Option A: a dedicated AI Research Desk page, with a lightweight navigation and/or dashboard affordance pointing to it.

This keeps the homepage from becoming overloaded while giving the AI workflow enough room for symbol selection, macro context, recommendation-signal context, assistant output, diagnostics, and safety wording.

## User Value

- The user can open one focused page for AI-assisted stock research.
- The user can select stocks from existing watchlist data, existing deterministic recommendation signals, or manual symbol entry.
- The user can ask for an AI/fallback research summary without visiting each instrument detail page first.
- Existing macro indicators, including Buffett Indicator rows when available, can shape the research context.
- The UI makes clear which outputs are evidence-backed and which are deterministic technical research signals.

## Confirmed Repository Facts

- Single-instrument AI assistant already exists:
  - backend service: `packages/services/market_assistant.py`
  - LLM/fallback prompt logic: `packages/ai/market_assistant.py`
  - API route: `POST /assistant/market`
  - web proxy: `apps/web/app/api/assistant/market/route.ts`
  - component: `apps/web/components/market-assistant-card.tsx`
- The current assistant is scoped to `scope="instrument"` and `timeframe="1d"`.
- Assistant evidence already includes daily bars, technical indicators, fundamentals, news, generated reports, and reviewed/citable research source notes.
- Assistant citation validation rejects unknown LLM citation IDs and falls back to deterministic output.
- Smart recommendation signals already exist:
  - service: `packages/services/smart_recommendations.py`
  - API tests: `tests/api/test_recommendations_api.py`
  - web component: `apps/web/components/smart-recommendations.tsx`
- Current recommendation signal types are `breakout`, `volume_anomaly`, `oversold_rebound`, and `strong_momentum`.
- Homepage market overview already includes macro indicators, source readiness, dashboard brief, and followed/watchlist market context through `GET /dashboard/market-overview`.
- Watchlist storage and UI already exist under `/watchlist` and related API routes.
- Current navigation is centralized in `apps/web/components/navigation-items.ts`, with exact href coverage tested in `apps/web/components/navigation-items.test.ts`.
- The existing `SmartRecommendations` component contains hardcoded visible Chinese copy and should not be expanded without localization cleanup.
- User manual and runbook text already state that AI outputs are research assistance only and must not become trading instructions.

## Requirements

### R1. Dedicated AI Research Desk Entry

- Add a visible AI Research Desk entry in navigation and/or the dashboard.
- The first screen should be the usable research workflow, not a marketing landing page.
- The page should feel like a personal research cockpit: compact, source-aware, and oriented around choosing symbols and asking AI.

### R2. Stock Selection

- Let the user select or enter at least one stock symbol.
- Reuse watchlist items and recommendation signal symbols where possible.
- Keep the MVP bounded to a small number of selected symbols so latency, UI density, and citation review remain manageable.
- If multiple symbols are selected, the first implementation may analyze one active symbol at a time while preserving selected-symbol context for later comparison.

### R3. AI Research Summary

- Let the user request an AI/fallback research summary for the active selected stock.
- Reuse the existing market assistant request path and evidence gates.
- The prompt and/or visible UI context should steer the summary toward:
  - why the stock is being surfaced;
  - latest evidence available;
  - macro/context considerations when available;
  - risks and data gaps;
  - follow-up research questions.

### R4. Recommendation Framing

- Recommendation-like language must be framed as research ideas or technical signals, not investment instructions.
- The UI must not present buy/sell/hold, target price, position sizing, execution steps, or broker workflow.
- Existing deterministic recommendation signals may be shown as inputs, but they must remain clearly labeled as unbacktested or source-dependent technical research signals unless the payload proves otherwise.

### R5. Macro Context And Source Gaps

- Show relevant macro context from the market overview payload when available, including favorite macro indicators and Buffett Indicator rows for US/CN/HK where present.
- Show source gaps and diagnostics as gaps, not as evidence.
- Source-readiness rows, seed templates, macro source capability rows, collection links, and unsupported source gaps must remain non-citable.

### R6. Evidence And Citation Boundaries

- AI may cite only allowed local evidence IDs already supported by the assistant/dashboard evidence layer.
- Missing data must produce diagnostics or gap wording, not fabricated conclusions.
- The page must preserve the assistant safety payload and make the no-investment-advice boundary visible.

### R7. Localization

- User-facing copy introduced by the new page or touched recommendation UI must be localized in English and Chinese through the existing `next-intl` message files.
- Existing mojibake or hardcoded visible strings in reused AI/recommendation surfaces should be corrected when they appear in the new workflow.

## Acceptance Criteria

- [ ] User can reach a dedicated AI Research Desk page from visible navigation and/or dashboard affordance.
- [ ] User can select or enter at least one stock symbol.
- [ ] User can request an AI/fallback research summary for the active selected symbol.
- [ ] Existing assistant evidence/citation validation is reused or preserved.
- [ ] Existing recommendation signals can be surfaced as research inputs without being converted into trading instructions.
- [ ] Macro/context data and source gaps are shown when available, without treating non-citable guidance as evidence.
- [ ] The page shows explicit research-only safety wording and avoids buy/sell/hold, target price, sizing, and execution language.
- [ ] UI text introduced or touched by this slice is localized in English and Chinese.
- [ ] Tests cover the new route/entry point, symbol selection, summary request behavior, diagnostics/gap rendering, safety wording, and navigation coverage.
- [ ] Validation includes relevant backend tests if service/API contracts change, frontend tests, TypeScript, `git diff --check`, and Trellis task validation.

## Out Of Scope

- Buy/sell/hold recommendations.
- Target prices, position sizing, trade execution, broker integration, or automated portfolio allocation.
- New paid data integrations.
- Full multi-symbol LLM portfolio optimizer.
- Realtime quote, Level-2, order-flow, or execution-grade recommendation engine.
- New document corpus ingestion.
- Replacing the existing single-instrument assistant backend in the first slice.
