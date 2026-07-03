# Phase 2 Hardening Acceptance Closure Design

## Boundaries

This task hardens already-visible Phase 2 features without introducing new large provider integrations.

In scope:

- Advanced K-line chart control gaps.
- Dashboard recommendation actionability and tests.
- Hot-sector payload/status labelling.
- Comparison export usefulness.

Out of scope:

- Full real sector data provider integration beyond a clear status/source contract.
- Phase 3 intraday, market depth, technical workbench, or AI assistant work.

## Frontend Design

- Keep chart work inside `AdvancedCandlestickChart` unless a smaller utility is needed.
- Keep recommendation and sector labels localized through `apps/web/messages/en.json` and `apps/web/messages/zh.json`.
- Recommendation cards should use existing route helpers or Next links to navigate to `/instruments/{symbol}`.
- Comparison export should include selected summaries and correlation matrix data in the generated text file.

## Backend/API Design

- Recommendation tests should construct deterministic bar series that trigger breakout and oversold/rebound categories.
- Hot-sector API payloads should include explicit status/source metadata. If only demo data is returned, it must be labelled as degraded/mock/demo rather than ok/live.

## Compatibility

- Existing dashboard content and tests must continue to pass.
- Existing API consumers should tolerate added fields.
- The chart should continue to support dark mode and the lightweight-charts v5 API.

## Rollback

All changes are localized to Phase 2 UI/API/test files. If one sub-area fails, revert that sub-area while keeping independently verified changes.
