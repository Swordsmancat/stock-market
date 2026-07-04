# Feature Completion Audit Manual and Roadmap Design

## Scope

This task is an audit, documentation, and roadmap task for the requested Phase 2 and Phase 3 financial-platform capabilities. It does not attempt to implement every missing large feature in one batch. Instead, it produces evidence-based completion status, updates stable manuals with accurate capability boundaries, and creates Trellis-backed follow-up work for gaps that require dedicated implementation.

## Inputs

- Repository code and tests under `apps/`, `packages/`, and `tests/`.
- Existing user/developer documentation under `README.md` and `docs/`.
- Trellis task artifacts under `.trellis/tasks/` and `.trellis/tasks/archive/`.
- Recent commits that implemented Phase 2 / Phase 3 slices.
- Professional platform benchmarks from sources describing TradingView, Bloomberg Terminal, stock screeners, AI research tools, and broker/trading terminals.

## Completion Matrix Contract

Each feature is classified with this status model:

- `Complete`: code, UI/API integration, and tests support the requested MVP behavior.
- `Partial`: a user-visible or API contract exists, but the requested capability is degraded, provider-limited, or not backed by real data.
- `Missing`: no stable implementation evidence exists.
- `Unclear`: repository evidence is insufficient and the item needs manual verification.

The matrix records:

- Feature name.
- Phase.
- Completion status.
- Evidence paths.
- Current limitation.
- Recommendation: archive/keep/create follow-up Trellis task.

## Documentation Strategy

Add stable documentation without overstating incomplete features:

- `docs/manual/user-guide.md`: product-facing usage guide and feature status.
- `docs/runbooks/developer-maintenance.md`: maintainer guide for API endpoints, degraded-safe provider contracts, tests, and provider capability notes.
- `README.md`: small documentation index and updated feature-status summary.

Documentation must distinguish:

- Fully implemented features.
- Degraded-safe contracts that intentionally do not fabricate unsupported data.
- Planned or missing features, especially the AI assistant.

## Professional Benchmark Strategy

Use a balanced comparison baseline:

- TradingView-style charting and technical-analysis platforms.
- Bloomberg/Koyfin/AlphaSense-style research terminals.
- Stock screener and broker terminal workflows.
- CN retail terminal expectations such as intraday chart, level-2/depth, hot sectors, and fund flow.

Comparison dimensions:

- Market-data integrity and real-time coverage.
- Chart interaction and indicator depth.
- Screeners, recommendations, and alerts.
- Market breadth and sector rotation.
- Fundamental/news/AI research workflows.
- Explainability, citations, degraded-state transparency, and operational readiness.

## Trellis Follow-up Task Strategy

Large incomplete features become separate Trellis tasks rather than hidden inside this audit task:

- AI market assistant implementation.
- Real intraday minute-bar provider/data pipeline.
- Real market-depth and large-order provider/data pipeline.
- Real hot-sector fund-flow backend/provider support.
- Optional Trellis state reconciliation for already implemented tasks.

## Risk Controls

- Do not include unrelated `apps/web/app/api/recommendations/route.ts` line-ending noise.
- Do not claim real-time or level-2 market data support where only degraded-safe contracts exist.
- Do not describe AI assistant as available unless an actual API/UI/test implementation exists.
- Keep documentation factual and status-labelled.
