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

- [ ] `design.md` defines historical-bar inputs, signal snapshot semantics, benchmark selection, and output metrics.
- [ ] `implement.md` sequences service, API, UI, tests, and documentation.
- [ ] Backend tests cover each current signal type with deterministic historical bars.
- [ ] API or service output includes sample size, forward windows, and failure/no-data diagnostics.
- [ ] Frontend presentation distinguishes evaluated signals from unevaluated realtime recommendations.
- [ ] Documentation records limitations around survivorship bias, data gaps, and non-advice usage.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
