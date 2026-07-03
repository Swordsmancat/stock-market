# Phase 2 and 3 Financial Features Completion Design

## Boundaries

This coordination task does not own direct feature implementation. It owns the acceptance matrix, child-task routing, cross-task ordering, and final integration review.

Implementation belongs to child tasks:

- `07-04-phase2-hardening-acceptance-closure`
- `07-04-technical-indicators-workbench`
- `07-04-intraday-chart`
- `07-04-market-depth-data`
- `07-04-ai-market-assistant`
- `07-03-performance-data-fix`

## Cross-Cutting Contracts

### Localization

All user-visible labels added in `apps/web` must be present in both `apps/web/messages/en.json` and `apps/web/messages/zh.json`.

### Data Availability

Financial features must distinguish these states:

- `ok`: real or computed data is available.
- `degraded`: fallback data or partial provider support is being used.
- `unavailable`: provider support or source data is missing.

Mock data may be used in tests and demos only when explicitly labelled as mock or demo data.

### Provider Capability

Features that depend on provider-specific support must surface capability limits instead of failing silently. This especially applies to sectors, intraday, level-2 depth, tick data, and AI context retrieval.

### Testing

Each completed slice needs focused automated coverage at its highest-risk boundary:

- Frontend interaction and localization tests for UI-only slices.
- API route tests for client-facing proxies.
- Backend service/API pytest coverage for provider or calculation changes.

## Ordering

1. Phase 2 hardening: low-risk closure of already-visible features.
2. Technical indicators workbench: uses existing analytics and chart foundations.
3. Intraday chart: introduces new minute-data contracts and fallback UI.
4. Market depth data: research-gated because provider support may be unavailable.
5. AI market assistant: high product/compliance surface, implemented after data context contracts are clearer.

## Rollback Shape

Each child task should be committed as a separate slice. If a later slice fails, revert only that slice and keep earlier verified slices intact.
