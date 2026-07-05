# Recommendation Backtesting and Signal Evaluation - Implementation Plan

## Execution Order

1. Re-read recommendation service, API router, frontend component/proxy, existing tests, and documentation before editing.
2. Identify current signal generation thresholds and data assumptions for breakout, oversold rebound, volume anomaly, and strong momentum.
3. Add a small service-level evaluation model that accepts deterministic historical bars and forward windows.
4. Generate signal snapshots from historical bars using current signal semantics without calling live providers.
5. Compute research metrics: sample size, hit rate, forward returns, max drawdown, benchmark-relative return when benchmark data exists, and diagnostics.
6. Add deterministic service tests for each current signal type and no-data/insufficient-history states.
7. Decide whether API/UI exposure is small enough for this slice. If added, clearly label metrics as historical research evaluation.
8. Update user/developer docs with limitations: sample size, survivorship bias, data gaps, no advice, no trading automation.
9. Run focused backend tests first, then broader recommendation/API/frontend tests if touched.
10. Record deferred persistence/API/UI/portfolio-simulation work as follow-up notes instead of expanding scope mid-task.

## Files To Inspect Before Editing

- `packages/services/smart_recommendations.py`
- `apps/api/routers/recommendations.py`
- `apps/web/components/smart-recommendations.tsx`
- `apps/web/app/api/recommendations/route.ts`
- Existing recommendation tests under `tests/services/`, `tests/api/`, and `apps/web/**`.
- `docs/manual/user-guide.md`
- `docs/runbooks/developer-maintenance.md`

## First Slice Checklist

- [x] Identify existing signal types and threshold semantics.
- [x] Add typed evaluation dictionaries for snapshots and metrics.
- [x] Implement deterministic signal scanning over historical bars.
- [x] Implement forward return and hit-rate calculations.
- [x] Implement max drawdown after signal calculation.
- [x] Add benchmark-relative return only when benchmark bars align safely.
- [x] Add diagnostics for insufficient bars, invalid windows, no signals, and missing benchmark.
- [x] Add deterministic backend tests for all signal types and no-data states.
- [x] Update docs to prevent overclaiming predictive quality.

## Completed Implementation Notes

- Added `evaluate_recommendation_signals` in `packages/services/smart_recommendations.py` as a service-level, deterministic, research-only evaluation entry point.
- Reused current signal semantics from `RecommendationEngine` for `breakout`, `volume_anomaly`, `oversold_rebound`, and `strong_momentum` while scanning historical slices.
- Added signal snapshots with symbol, signal type, signal date, bar index, entry price, confidence, reason, source window, and data-points-used metadata.
- Added per-window metrics for sample size, skipped count, hit rate, average/median forward return, max drawdown after signal, and benchmark-relative return when benchmark data aligns.
- Added explicit diagnostics for insufficient history, invalid windows, no signal snapshots, insufficient post-signal bars, and unavailable benchmark data.
- Kept this slice service-only for historical metrics; no persistence, schema migration, scheduled lifecycle, or public API contract was added.
- Updated the dashboard recommendation card copy to distinguish current realtime technical signals from service-level historical evaluation.
- Updated user and maintainer docs with sample-size, survivorship-bias, data-gap, benchmark, and non-advice limitations.

## Completed Validation

```powershell
python -m pytest tests/services/test_recommendation_signal_evaluation.py tests/api/test_recommendations_api.py -q
# 11 passed

npm run test:web
# 101 passed

git diff --check -- packages/services/smart_recommendations.py tests/services/test_recommendation_signal_evaluation.py docs/manual/user-guide.md docs/runbooks/developer-maintenance.md
# no output / no whitespace errors
```

## Deferred Follow-ups

- Persistent signal-history tables and migrations.
- Scheduled signal evaluation lifecycle.
- Public API and dashboard UI if the first slice remains service-only.
- Portfolio simulation, slippage, transaction costs, and benchmark universe controls.
- Walk-forward validation and parameter optimization.
- Custom strategy scripting.

## Validation Commands

Start with focused recommendation tests:

```powershell
python -m pytest tests/services -q -k "recommendation or backtest or signal"
```

Run API tests if the router contract changes:

```powershell
python -m pytest tests/api/test_recommendations_api.py -q
```

Run frontend tests if dashboard cards change:

```powershell
npm run test:web -- apps/web/components/smart-recommendations.test.tsx apps/web/app/api/recommendations/route.test.ts
```

## Rollback Points

- After service model and focused service tests.
- After API contract changes, if any.
- After frontend rendering changes, if any.
- After documentation updates.

## Out-Of-Scope Unless Explicitly Approved

- Brokerage execution, order placement, or trade recommendation language.
- Live-provider or network-dependent tests.
- Database schema changes for signal history.
- Professional strategy-tester parity in a single slice.
