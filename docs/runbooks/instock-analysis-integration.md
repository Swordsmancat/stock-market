# InStock Analysis Integration

This project uses `myhhub/stock` as a staged analysis reference, not as a drop-in
runtime dependency.

## Current Slice

- Source reviewed: `myhhub/stock` at commit `b6e0ca2268cfbadd02f5ed052159c187b6670231`.
- Upstream license: Apache-2.0.
- Implemented feature: expanded no-dependency daily technical indicators.
- Implemented feature: stored `candlestick_patterns` technical indicator.
- Implemented feature: stored `chip_distribution` technical indicator, inspired
  by InStock's CYQ / chip-distribution capability.
- Implemented feature: research-only local composite stock selection API.
- Implemented feature: composite stock selection over additional stored
  technical evidence: candlestick pattern codes, MFI, William %R, and
  chip-distribution benefit ratio.
- Implemented feature: watchlist-scoped composite stock selection over active
  default-watchlist entries.
- Implemented feature: research-only `GET /strategies/screen` strategy screening API.
- Implemented feature: research-only `GET /strategies/evaluate` strategy evaluation API.
- Rule set: `candlestick_patterns_v1`.
- CYQ rule set: `chip_distribution_v1`.
- Composite stock selection rule set: `instock_composite_selection_v1`.
- First supported pattern codes:
  - `bullish_engulfing`
  - `bearish_engulfing`
  - `hammer`
  - `shooting_star`
  - `doji`
- Strategy screening rule set: `instock_strategy_screening_v1`.
- Expanded indicator codes:
  - `cci`
  - `obv`
  - `roc`
  - `bias`
  - `mfi`
  - `william_r`
- First supported strategy codes:
  - `volume_price_breakout`
  - `turtle_breakout`
  - `ma_trend_up`

The implementation is pure Python/pandas and does not install TA-Lib or import
InStock's indicator runtime, database, scheduler, proxy/cookie, Tornado UI, or
trade modules.

The first CYQ slice uses local daily OHLCV bars only. Because this project does
not yet store free-float shares or true turnover rate, `chip_distribution` is a
volume-normalized research approximation with
`approximation="volume_weighted_without_float_shares"`. Do not describe it as a
provider-grade chip distribution until reviewed float-share and turnover inputs
exist.

## Evidence Boundary

Candlestick patterns are research signals only. They can be included in stored
technical-indicator evidence after `/indicators/recalculate` writes a local
`TechnicalIndicator` row. They are not trading advice and must not generate
buy/sell/hold language, target prices, position sizing, order intents, or broker
execution.

Expanded technical indicators and `chip_distribution` follow the same evidence
boundary. They can be cited only as stored local technical indicators and, for
CYQ, only with its approximation limitation. They must not be used to claim
institution-grade cost concentration, predict support/resistance, or produce
trading actions.

`GET /stock-selection/screen` is a local evidence screener. It reads stored
`Instrument`, `DailyBar`, `TechnicalIndicator`, and `FundamentalSnapshot` rows,
then returns matched criteria and stored evidence citation IDs. The screener
does not fetch live providers, does not persist selection results, and does not
turn a match into a buy/sell/hold recommendation.

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
- add more technical indicators only when formulas are pure, tested, and do not
  require TA-Lib/runtime imports;
- refine CYQ only after reviewed free-float/turnover data is available;
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

## Composite Stock Selection API

`GET /stock-selection/screen` screens local stored instruments against
fundamental and technical criteria:

```text
GET /stock-selection/screen?symbols=AAPL,MSFT&watchlist_only=true&max_pe_ratio=30&min_revenue_growth=0.1&min_rsi=40&max_rsi=70&require_price_above_ma=true&required_pattern_codes=hammer&min_mfi=50&min_chip_benefit_ratio=0.6
```

The first criteria are:

- `max_pe_ratio`
- `min_revenue_growth`
- `min_net_margin`
- `min_rsi`
- `max_rsi`
- `require_price_above_ma`
- `required_pattern_codes`
- `min_mfi`
- `max_mfi`
- `min_william_r`
- `max_william_r`
- `min_chip_benefit_ratio`
- `max_chip_benefit_ratio`
- `watchlist_only` to limit candidate instruments to active default-watchlist
  entries before criteria evaluation

At least one criterion is required. Missing local bars, fundamentals, or
technical indicators produce diagnostics and no fabricated match. Nested
criteria read only stored `candlestick_patterns.patterns[]` and
`chip_distribution.benefit_ratio` payloads. Returned `evidence_citations` point
to stored rows used in the screen, while the selection result itself remains a
research-only analysis payload.

`watchlist_only` is a candidate-scope flag, not evidence. It reads active
watchlist `symbol`/`market` pairs without provider-backed watchlist enrichment
and still requires the ordinary stored evidence rows before a symbol can match.

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
pytest tests/services/test_stock_selection.py tests/api/test_stock_selection_api.py
python -m ruff check packages/analytics/indicators.py packages/analytics/candlestick_patterns.py packages/analytics/chip_distribution.py packages/services/indicators.py packages/services/strategy_screening.py packages/services/stock_selection.py apps/api/routers/strategy_screening.py apps/api/routers/stock_selection.py tests/analytics/test_indicators.py tests/services/test_indicator_persistence_service.py tests/services/test_strategy_screening.py tests/services/test_stock_selection.py tests/api/test_indicators_db_api.py tests/api/test_strategy_screening_api.py tests/api/test_stock_selection_api.py
git diff --check
```
