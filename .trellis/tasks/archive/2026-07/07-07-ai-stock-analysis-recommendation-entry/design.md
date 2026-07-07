# AI stock analysis and recommendation entry design

## Architecture

Build a dedicated localized route under the existing Next.js app, likely `apps/web/app/[locale]/ai-research/page.tsx`, backed primarily by existing frontend proxy/API paths.

The first slice should be frontend-composition first:

- Server page fetches initial context from existing backend endpoints.
- Client component manages symbol selection, manual symbol entry, active symbol selection, and assistant request interaction.
- Existing `POST /api/assistant/market` remains the only AI summary request path.
- Existing market overview, watchlist, and recommendation APIs provide context and candidate symbols.

No new backend contract is required for the first slice unless implementation discovers that an existing payload cannot supply required data.

## Boundaries

### Frontend

- Add navigation entry through `apps/web/components/navigation-items.ts`.
- Add localized messages in `apps/web/messages/en.json` and `apps/web/messages/zh.json`.
- Add the AI Research Desk route and focused tests under `apps/web/app/[locale]/ai-research/`.
- Prefer a new client component for the desk workflow rather than overloading the homepage.
- Reuse `askMarketAssistant` from `apps/web/lib/market-assistant.ts`.
- Reuse the existing assistant response shape and safety/citation panels. If the existing `MarketAssistantCard` is too single-symbol/opinionated, extract small reusable display pieces instead of duplicating response rendering.
- Treat the current `SmartRecommendations` component carefully: it has hardcoded visible strings and should either be localized in this slice or only used through a small localized desk-specific signal list.

### Backend

- Keep backend unchanged for the MVP if possible.
- If backend changes become necessary, they must preserve `scope="instrument"` assistant behavior and existing citation validation.
- Do not add multi-symbol recommendation/portfolio optimizer semantics in this slice.

## Data Flow

1. User opens `/[locale]/ai-research`.
2. Server page fetches:
   - `/watchlist` for saved symbols;
   - `/dashboard/market-overview?provider=<settings provider>` for followed symbols, macro indicators, dashboard brief, diagnostics, and source gaps;
   - `/recommendations?symbols=<candidate symbols>&limit=<small limit>` for deterministic technical signal candidates.
3. Page renders candidate chips/tables:
   - watchlist symbols;
   - recommendation signal symbols;
   - optional followed symbols from market overview;
   - manual input.
4. User selects one or more symbols and chooses an active symbol.
5. Client sends `askMarketAssistant({ scope: "instrument", symbol: activeSymbol, question, timeframe: "1d", locale, provider })`.
6. Response renders:
   - answer markdown;
   - assistant status;
   - allowed citations;
   - diagnostics;
   - context metrics;
   - safety disclaimer.

## UI Shape

The page should be a work surface, not a landing page:

- Header band: title, concise research-only disclaimer, provider/source freshness badges.
- Left or top selection area: manual symbol input, watchlist candidates, recommendation-signal candidates.
- Main panel: active symbol AI prompt and response.
- Context panel: macro indicators, Buffett Indicator rows when available, dashboard brief/source gap snippets, recommendation signal rationale.
- Diagnostics area: missing data, provider/source warnings, and non-citable source gaps.

Cards may be used for individual panels, but avoid nesting cards inside cards. Use compact spacing and table/list layouts for scanability.

## Safety And Evidence Rules

- Use "research idea", "technical signal", "context", and "follow-up question" language.
- Do not introduce "buy", "sell", "hold", target price, sizing, or execution copy in user-facing strings.
- Source gaps, collection links, seed templates, and source readiness rows must remain explanatory context only.
- Any assistant citation shown on the page must come from the existing assistant response citation list.
- Missing macro values should be rendered as unavailable/source gap, not estimated.

## Compatibility

- The existing instrument detail assistant remains available and unchanged.
- Existing homepage recommendations remain available; this task only adds a dedicated AI research workflow and may improve localization if reused.
- Existing tests for navigation exact hrefs must be updated intentionally when adding `/ai-research`.
- Existing dirty files must be inspected before editing to avoid overwriting user or parallel changes.

## Rollout And Rollback

- Rollout is additive: a new route plus navigation/dashboard affordance.
- Rollback is straightforward: remove the nav item, route, new component/messages, and tests.
- If backend contracts are untouched, risk is limited to frontend routing/UI behavior.
