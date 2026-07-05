# Recommendation Backtesting and Signal Evaluation - Design

## Scope

Add a deterministic, research-only evaluation layer for existing recommendation signals. The first implementation slice should evaluate current signal types against historical daily bars without adding trading, brokerage, live-provider dependency, or persistent signal storage.

## Current Entry Points

- Recommendation service: `packages/services/smart_recommendations.py`
- Recommendation API: `apps/api/routers/recommendations.py`
- Dashboard UI: `apps/web/components/smart-recommendations.tsx`
- Dashboard proxy/page usage under `apps/web/app/api/recommendations` and `apps/web/app/[locale]/page.tsx`
- Existing recommendation tests under `tests/api/` and `tests/services/`
- User and maintainer docs: `docs/manual/user-guide.md`, `docs/runbooks/developer-maintenance.md`

## Evaluation Model

The evaluation layer should be explicit about what is and is not being evaluated.

### Inputs

- Historical OHLCV bars for one or more symbols.
- Current deterministic recommendation signal definitions:
  - breakout
  - oversold rebound
  - volume anomaly
  - strong momentum
- Forward return windows, for example 1, 5, and 20 bars.
- Optional benchmark bars when available.

### Signal Snapshot Semantics

Each evaluated signal should have a snapshot record with:

- `symbol`
- `signal_type`
- `signal_date`
- `entry_price`
- `confidence` or deterministic signal score when available
- `reason`
- `source_window`
- `data_points_used`

The snapshot is a research observation, not a trade entry or order.

### Output Metrics

Evaluation output should include:

- `sample_size`
- `forward_windows`
- `hit_rate` per window using positive forward return as the initial definition
- `average_forward_return`
- `median_forward_return` when practical
- `max_drawdown_after_signal` over the configured window
- `benchmark_relative_return` when benchmark bars are available
- `coverage` and no-data diagnostics

### Diagnostics

The service should clearly report why evaluation cannot be produced:

- not enough historical bars
- no signal snapshots matched the configured signal type
- benchmark unavailable
- invalid forward window
- insufficient post-signal bars

Diagnostics must not convert missing evidence into zero returns.

## Storage Boundary

The first slice should not add database tables. It may expose service-level evaluation from in-memory deterministic bars or existing fetched bars. Persistent signal history requires a separate design because it needs:

- schema/migration ownership
- signal versioning
- benchmark selection policy
- survivorship-bias controls
- scheduled evaluation lifecycle

## API / UI Boundary

The first slice can be service-only if API/UI scope is too large. If API/UI is added, it must:

- expose evaluation as research metrics, not advice;
- distinguish evaluated historical signals from live/current recommendations;
- show sample size and no-data diagnostics prominently;
- avoid implying future performance.

## Professional Benchmark Boundary

Professional platforms often include strategy tester, scanner backtests, and signal hit-rate analytics. This task should make the first reliable step toward that by adding deterministic metrics and documentation, while deferring:

- parameter optimization;
- portfolio simulation;
- transaction costs and slippage;
- survivorship-bias corrected universes;
- walk-forward validation;
- strategy marketplace or custom scripting.

## Compatibility

- Existing recommendation endpoint and dashboard cards must keep working.
- Existing recommendation signal names should remain stable.
- Tests must use deterministic fixture bars and must not call live providers.

## Risks

- Users may overinterpret hit rate. UI/docs must label metrics as historical research evaluation.
- Small sample sizes can be misleading; sample size and coverage must be visible.
- Adding persistence prematurely can lock in weak signal semantics.
