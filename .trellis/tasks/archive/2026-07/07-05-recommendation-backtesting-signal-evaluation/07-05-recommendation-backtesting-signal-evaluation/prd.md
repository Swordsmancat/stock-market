# Recommendation Backtesting and Signal Evaluation

## Goal

Add professional evaluation for recommendation signals: backtests, hit rate, drawdown, benchmark comparison, and explainable signal history.

## Requirements

- Build on `packages/services/smart_recommendations.py`, `/recommendations`, and the dashboard recommendation UI.
- Define a backtesting model for current signal types: breakout, oversold rebound, volume anomaly, and strong momentum.
- Produce outcome metrics such as hit rate, forward return windows, max drawdown, benchmark-relative return, and sample size.
- Persist or expose signal history only after the storage/API boundary is designed.
- Clearly label results as research evaluation, not investment advice or automated trading.
- Keep tests deterministic and independent from live provider network access.

## Acceptance Criteria

- [x] `design.md` defines historical-bar inputs, signal snapshot semantics, benchmark selection, and output metrics.
- [x] `implement.md` sequences service, API, UI, tests, and documentation.
- [x] Backend tests cover each current signal type with deterministic historical bars.
- [x] API or service output includes sample size, forward windows, and failure/no-data diagnostics.
- [x] Frontend presentation distinguishes evaluated signals from unevaluated realtime recommendations.
- [x] Documentation records limitations around survivorship bias, data gaps, and non-advice usage.

## Completion Notes

- Added service-level deterministic `evaluate_recommendation_signals` for `breakout`, `volume_anomaly`, `oversold_rebound`, and `strong_momentum`.
- Evaluation uses caller-supplied historical bars only; it does not call live providers, write storage, or expose a new public API in this slice.
- Output includes signal snapshots, sample size, configured forward windows, hit rate, average/median forward returns, max drawdown after signal, optional benchmark-relative return, diagnostics, and a research-only disclaimer.
- Dashboard recommendation cards now explicitly describe current recommendations as realtime technical signals without attached historical evaluation, keeping them distinct from service-level historical metrics.
- User and maintainer documentation records sample-size limits, survivorship bias, data gaps, benchmark limitations, and non-advice usage.

## Validation

```powershell
python -m pytest tests/services/test_recommendation_signal_evaluation.py tests/api/test_recommendations_api.py -q
# 11 passed

git diff --check -- packages/services/smart_recommendations.py tests/services/test_recommendation_signal_evaluation.py docs/manual/user-guide.md docs/runbooks/developer-maintenance.md
# no output / no whitespace errors
```

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
