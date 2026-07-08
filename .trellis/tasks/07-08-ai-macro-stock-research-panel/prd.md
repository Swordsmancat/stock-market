# AI Macro Stock Research Desk

## Goal

Enhance the existing AI Research Desk so a personal investor can select stocks, see relevant macro and valuation context, and ask the AI assistant for evidence-bound summaries that include stored macro indicator evidence when available.

The feature must reinforce the product direction: personal information aggregation, macro indicator collection, hard-to-find source readiness, and AI synthesis. It must not become a professional trading terminal.

## Background

- The user wants macro indicators such as Buffett Indicator, rates, inflation, liquidity, and official/API-sourced data to be prominent, including homepage favorites and AI research context.
- The user wants AI recommendation and summary ability to stand out, but as research leads and summaries, not buy/sell/hold advice.
- The app already has an AI Research Desk page that loads `/watchlist`, `/dashboard/market-overview`, and `/recommendations` before rendering `AiResearchDesk` (`apps/web/app/[locale]/ai-research/page.tsx:58`, `apps/web/app/[locale]/ai-research/page.tsx:69`, `apps/web/app/[locale]/ai-research/page.tsx:76`).
- `AiResearchDesk` already supports selected symbols, manual symbol entry, macro context, source gaps, recommendations, and the existing `MarketAssistantCard` (`apps/web/components/ai-research-desk.tsx:122`, `apps/web/components/ai-research-desk.tsx:128`, `apps/web/components/ai-research-desk.tsx:312`, `apps/web/components/ai-research-desk.tsx:329`).
- The dashboard already builds `market_indicator:<code>:<as_of>` citations for stored macro observations and includes macro/valuation indicators in the market overview payload (`packages/services/market_dashboard.py:281`, `packages/services/market_dashboard.py:965`, `packages/services/market_dashboard.py:966`).
- The instrument assistant currently builds evidence from price bars, technical indicators, fundamentals, news, generated reports, and reviewed research source notes, but not stored `MarketIndicatorObservation` macro evidence (`packages/services/market_assistant.py:135`, `packages/services/market_assistant.py:151`, `packages/services/market_assistant.py:161`).
- The assistant citation validator does not currently accept `market_indicator:` IDs (`packages/services/market_assistant.py:34`).
- The AI Research Desk localization already frames the page as research only and asks the assistant to include macro context and missing data (`apps/web/messages/en.json:877`, `apps/web/messages/en.json:906`, `apps/web/messages/zh.json:884`, `apps/web/messages/zh.json:913`).

## Requirements

### R1. Citable macro evidence in instrument assistant

- When a database session is available, the instrument assistant should load stored macro and valuation observations from the existing market indicator service.
- The assistant should include a concise macro summary in its prompt context.
- Stored observations that have value, as-of date, and source metadata should become allowed citations with IDs shaped as `market_indicator:<code>:<as_of>`.
- Favorite macro indicators should be prioritized when possible, followed by Buffett Indicator, rates, inflation, and liquidity indicators.
- Missing macro observations should produce diagnostics or gap context, but must not become citations.
- Official source readiness, collection links, and seed templates remain guidance only and must not be cited as evidence.

### R2. Official source readiness on AI Research Desk

- The AI Research page should fetch the existing `/market-indicators/official-sources/status` endpoint.
- The UI should surface concise FRED and World Bank readiness / next-action context near macro evidence or source gaps.
- Readiness context should be visually and semantically distinct from citable macro observations.
- If the source status endpoint fails, the AI Research Desk should still render with existing watchlist, macro, and assistant behavior.

### R3. Research-first UX language

- Keep the page positioned as an AI research workspace for selected stocks and macro context.
- Avoid professional trading-terminal framing, execution workflows, target prices, position sizing, or direct trading instructions.
- Recommendation cards should continue to read as research signals or candidates, not trade recommendations.
- Macro indicators should clearly show whether they are local citable evidence or only a source/data gap.

### R4. Assistant starter question

- The assistant starter question should include citable macro context when present.
- It should also mention missing official source guidance when useful, while keeping those gaps out of citation claims.
- The wording must continue to request risks, missing data, and follow-up research questions instead of trading actions.

### R5. Safety and evidence boundaries

- No buy, sell, hold, short/long, position-sizing, target-price, or broker/execution workflow should be introduced.
- No fabricated macro or market values should be shown.
- AI claims must cite only stored/citable evidence made available to the assistant.
- Source readiness is a maintenance guide, not a factual citation source.

## Acceptance Criteria

- [ ] The assistant response payload can include `market_indicator:*` citations for stored macro observations.
- [ ] The assistant prompt includes a macro context section or equivalent summary built from stored macro indicator observations.
- [ ] Unknown or hallucinated `market_indicator:*` citation IDs trigger the same fallback validation behavior as unknown news/report citations.
- [ ] Missing macro observations are reported as data gaps or diagnostics and are not emitted as citations.
- [ ] The AI Research Desk loads and displays official source readiness / next-action status without breaking when that endpoint is unavailable.
- [ ] The UI distinguishes local macro evidence from source readiness guidance.
- [ ] The initial assistant question uses macro context and missing-source guidance without asking for trading instructions.
- [ ] English and Chinese messages are updated for any new visible UI text.
- [ ] Backend tests cover macro citations, missing macro observations, and invalid `market_indicator:*` citation validation.
- [ ] Frontend tests cover source status rendering and endpoint failure fallback.
- [ ] Existing homepage, Evidence Center, market overview, and assistant behavior remain backward compatible.

## Out of Scope

- Basket-level multi-symbol AI comparison summary. MVP keeps the existing active-symbol assistant and selected-symbol basket UI.
- Persistent daily/weekly AI digest history.
- Browser file upload, local document notebook expansion, or manual note upload workflows.
- New official macro adapters, scheduled refresh jobs, Redis caching, or realtime macro feeds.
- Professional charting terminal features, Level-2 data, order flow, broker execution, or trading automation.
- AI-generated buy/sell/hold recommendations, target prices, position sizing, or return guarantees.

## Planning Decision

No blocking product question remains for this MVP. The recommended implementation path is to enhance the existing AI Research Desk and existing instrument assistant instead of creating a new standalone panel.
