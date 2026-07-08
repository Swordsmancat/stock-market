# InStock Analysis Integration

This project uses `myhhub/stock` as a staged analysis reference, not as a drop-in
runtime dependency.

## Current Slice

- Source reviewed: `myhhub/stock` at commit `b6e0ca2268cfbadd02f5ed052159c187b6670231`.
- Upstream license: Apache-2.0.
- Implemented feature: stored `candlestick_patterns` technical indicator.
- Implemented feature: research-only `GET /strategies/screen` strategy screening API.
- Implemented feature: research-only `GET /strategies/evaluate` strategy evaluation API.
- Rule set: `candlestick_patterns_v1`.
- First supported pattern codes:
  - `bullish_engulfing`
  - `bearish_engulfing`
  - `hammer`
  - `shooting_star`
  - `doji`
- Strategy screening rule set: `instock_strategy_screening_v1`.
- First supported strategy codes:
  - `volume_price_breakout`
  - `turtle_breakout`
  - `ma_trend_up`

The implementation is pure Python/pandas and does not install TA-Lib or import
InStock's database, scheduler, proxy/cookie, Tornado UI, or trade modules.

## Evidence Boundary

Candlestick patterns are research signals only. They can be included in stored
technical-indicator evidence after `/indicators/recalculate` writes a local
`TechnicalIndicator` row. They are not trading advice and must not generate
buy/sell/hold language, target prices, position sizing, order intents, or broker
execution.

Live calculations, InStock feature lists, and source-readiness notes are not AI
citations by themselves. The citation boundary remains stored local evidence,
such as `technical_indicators:{symbol}:{as_of}`.

`GET /strategies/screen` results are research analysis payloads only. They are
not currently stored citation rows and must not be cited by the assistant as
verified evidence unless a future slice adds reviewed persistence with stable
source metadata.

## Extension Notes

Future InStock-inspired slices should stay independently verifiable:

- add more no-dependency pattern rules only with deterministic fixtures;
- add strategy screening as explainable research signals, not orders;
- use `GET /recommendations/evaluate` for current historical signal metrics;
- add deeper backtest statistics only after the input/output contract names return
  horizon, sample size, assumptions, transaction-cost policy, and survivorship limitations;
- keep automatic trading in a separate paper-trading-first safety track.

## Historical Signal Evaluation API

`GET /recommendations/evaluate` exposes the current deterministic recommendation
signal evaluator as a research endpoint:

```text
GET /recommendations/evaluate?symbol=AAPL&start=2026-01-01&end=2026-02-15&signal_types=breakout&forward_windows=1,5&provider=mock
```

It returns sample size, signal snapshots, per-window hit rate, average/median
forward return, max drawdown after signal, benchmark-relative return when a
benchmark is supplied, diagnostics, source metadata, and
`research_signal_only=true`.

This endpoint is not a production strategy tester. It does not model order
fills, slippage, fees, tax, borrow constraints, portfolio constraints, or live
execution.

## Strategy Screening API

`GET /strategies/screen` evaluates the latest daily OHLCV window against
deterministic InStock-inspired screening rules:

```text
GET /strategies/screen?symbols=AAPL,MSFT&strategies=turtle_breakout,ma_trend_up&start=2026-01-01&end=2026-03-31&provider=mock
```

The API returns flattened `items[]`, per-symbol payloads, provider metadata,
sanitized diagnostics, `research_signal_only=true`, and the disclaimer:
`Strategy screening signals are research aids only and are not investment advice.`

The first rules are adapted from InStock's strategy module shapes:

- `volume_price_breakout`: latest bar rises on high relative volume and sufficient traded amount.
- `turtle_breakout`: latest close sets a new high within the lookback window.
- `ma_trend_up`: 30-day moving average rises across 30/20/10/latest checkpoints.

These are not executable orders, backtest results, or validated trading strategies.

## Strategy Evaluation API

`GET /strategies/evaluate` scans historical bars for the same strategy screening
rules and reports bounded forward-return diagnostics:

```text
GET /strategies/evaluate?symbol=AAPL&start=2026-01-01&end=2026-03-31&strategies=volume_price_breakout&forward_windows=1,5&benchmark_symbol=SPY&provider=mock
```

It returns snapshots, per-window sample size, hit rate, average/median forward
return, max drawdown after signal, optional benchmark-relative return, provider
metadata, sanitized diagnostics, `research_signal_only=true`, and the same
non-advice disclaimer.

This endpoint is not a production backtest. It does not model fills, slippage,
fees, tax, borrow constraints, portfolio sizing, survivorship assumptions,
parameter optimization, scheduler execution, or broker orders.

## Validation

Use focused checks after changing this slice:

```powershell
pytest tests/analytics/test_indicators.py tests/services/test_indicator_persistence_service.py tests/api/test_indicators_db_api.py
pytest tests/api/test_recommendations_api.py tests/services/test_recommendation_signal_evaluation.py
pytest tests/services/test_strategy_screening.py tests/api/test_strategy_screening_api.py
python -m ruff check packages/analytics/candlestick_patterns.py packages/services/indicators.py packages/services/strategy_screening.py apps/api/routers/strategy_screening.py tests/analytics/test_indicators.py tests/services/test_indicator_persistence_service.py tests/services/test_strategy_screening.py tests/api/test_indicators_db_api.py tests/api/test_strategy_screening_api.py
git diff --check
```
