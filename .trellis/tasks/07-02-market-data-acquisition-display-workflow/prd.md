# Complete market data acquisition and display workflow

## Goal

Turn the current market-data MVP skeleton into a usable product workflow where a user can choose a provider, fetch daily market data for a specific symbol, see whether the data is real/mock/stale, inspect the data on a clear frontend page, and follow the resulting ingestion/analysis/report task state.

This task intentionally prioritizes product completeness over continuing low-risk API proxy test coverage. The first shippable workflow should be daily-bar based and honest about freshness. True real-time quote/level-1 market data can be added only after provider capabilities are explicit.

## Requirements

- Clarify product semantics:
  - `latest daily bar` is not the same as a real-time quote.
  - `mock`, `yfinance`, `akshare`, and `tushare` must be visibly distinguished when data is displayed.
  - User-facing UI must show source/provider/as-of/freshness where it affects trust.
- Make provider selection and readiness visible enough that users understand why data can or cannot be fetched.
- Support a practical daily-bars workflow:
  - choose or enter a symbol/market/provider;
  - trigger ingestion or analysis;
  - persist daily bars when a worker completes;
  - inspect latest price/history and task status;
  - generate or view a report based on those bars.
- Add a clear market data / instruments entry point instead of relying only on Dashboard, global search, reports, watchlist, or portfolios.
- Improve no-data and provider-error handling so empty provider responses do not become opaque 500 errors or silent empty states.
- Keep the first implementation slices incremental:
  - no broad schema migration unless a child task explicitly justifies it;
  - no real-network tests in CI;
  - no promise of real-time quotes until provider support is designed and tested.

## Acceptance Criteria

- [ ] Current backend and frontend product gaps are documented with concrete repository paths.
- [ ] A cross-layer design defines the daily-bars workflow from provider request through frontend display.
- [ ] The implementation plan is split into independently verifiable child tasks.
- [ ] The first implementation slice can be completed without schema migration or real provider network in tests.
- [ ] The plan explicitly distinguishes daily historical data, latest daily bar, and future real-time quote support.
- [ ] The plan identifies validation commands for backend services, frontend pages, worker tasks, and provider diagnostics.
- [ ] Product-facing empty/error states are called out as required work rather than treated as test-only polish.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
