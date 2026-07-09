# InStock-Inspired Strategy Screening And Evaluation Contract

## Scenario: Research-Only Strategy Screening And Historical Evaluation

### 1. Scope / Trigger

- Trigger: `GET /strategies/screen` evaluates the latest daily OHLCV window against
  deterministic, InStock-inspired screening rules.
- Trigger: `GET /strategies/evaluate` scans historical windows for the same rules and
  evaluates bounded forward-return diagnostics.
- Scope: API parsing in `apps/api/routers/strategy_screening.py`, market-data loading
  through `packages/services/market_data.py`, pure screening logic in
  `packages/services/strategy_screening.py`, and focused API/service tests.
- Non-goals: persisted strategy history, portfolio backtests, parameter optimization,
  broker order intents, automatic trading, TA-Lib installation, or vendoring
  `myhhub/stock`.

### 2. Signatures

- API:
  `GET /strategies/screen?symbols=AAPL,MSFT`
- API:
  `GET /strategies/evaluate?symbol=AAPL&start=YYYY-MM-DD&end=YYYY-MM-DD`
- Optional query fields:
  - `strategies`: comma-separated strategy codes from `volume_price_breakout`,
    `turtle_breakout`, and `ma_trend_up`.
  - `start` / `end`: optional historical bar window. If omitted, the API uses a
    365-day lookback ending today.
  - `provider`: optional market-data provider name.
  - `limit`: flattened match limit, bounded by the API route.
- Additional `/strategies/evaluate` query fields:
  - `forward_windows`: comma-separated positive integer forward windows in bars.
  - `benchmark_symbol`: optional symbol fetched over the same date window for relative returns.
- Service entry:
  `screen_latest_instock_strategies(symbol, bars, strategy_codes=None)`
- Service entry:
  `evaluate_instock_strategy_signals(symbol, bars, strategy_codes=None, forward_windows=None, benchmark_bars=None)`

### 3. Contracts

- The first strategy-screening slice supports:
  - `volume_price_breakout`, inspired by `instock.core.strategy.enter.check_volume`;
  - `turtle_breakout`, inspired by `instock.core.strategy.turtle_trade.check_enter`;
  - `ma_trend_up`, inspired by `instock.core.strategy.keep_increasing.check`.
- The implementation must remain pure Python over normalized OHLCV rows. It must not
  import InStock runtime code or add TA-Lib.
- All payloads must include `research_signal_only=true` and the disclaimer:
  `Strategy screening signals are research aids only and are not investment advice.`
- Strategy matches may include `confidence` as a static signal-strength score, but must not
  emit buy/sell/hold actions, target prices, position sizes, order intents, or execution
  instructions.
- Historical evaluation may return sample size, forward return, hit rate, return-distribution
  diagnostics, max drawdown, and benchmark-relative return. Per-window return-distribution
  diagnostics include `win_count`, `loss_count`, `flat_count`, `best_forward_return`,
  `worst_forward_return`, `positive_average_forward_return`,
  `negative_average_forward_return`, `return_stddev`, and `average_win_loss_ratio`.
  It must not model fills, fees, slippage, taxes, portfolio sizing, survivorship assumptions,
  or executable order lifecycle.
- API diagnostics expose provider/category and rule diagnostics only. They must not expose
  provider credentials or raw provider payloads.
- Strategy screening results are collection/analysis outputs, not stored citations. They become
  assistant-citable only if a future slice stores reviewed evidence rows with a stable citation path.

### 4. Validation & Error Matrix

- Empty `symbols` -> HTTP 400.
- Empty `/strategies/evaluate` `symbol` -> HTTP 400.
- `start > end` -> HTTP 400 before provider access.
- `/strategies/screen` provider boundary raises `MarketDataProviderError` -> route-level
  diagnostic with no exception.
- `/strategies/screen` provider boundary raises `ValueError` -> route-level invalid-request diagnostic.
- `/strategies/evaluate` provider boundary raises `MarketDataProviderError` -> HTTP 502 with
  provider/category only.
- `/strategies/evaluate` provider boundary raises `ValueError` -> HTTP 400.
- `/strategies/evaluate` `forward_windows` contains a non-integer -> HTTP 400 before provider access.
- No valid bars -> service payload `status="no_data"` with `NO_BARS`.
- Unknown strategy codes -> `UNKNOWN_STRATEGY_CODE` diagnostic and ignored.
- Not enough bars for a requested strategy -> `INSUFFICIENT_BARS` diagnostic.
- Not enough bars for historical evaluation -> `status="no_data"` with
  `NOT_ENOUGH_HISTORICAL_BARS`.
- Enough bars but no strategy match -> `status="no_match"` with `NO_STRATEGY_MATCH`.
- At least one rule matches -> `status="matched"` and `matches[]`.
- Historical evaluation finds no snapshots -> `status="no_signals"` with
  `NO_STRATEGY_SNAPSHOTS`.
- Historical snapshots exist but no future bars for a requested window ->
  `INSUFFICIENT_POST_SIGNAL_BARS`; missing benchmark bars never become zero relative return.

### 5. Good/Base/Bad Cases

- Good: `/strategies/screen?symbols=AAPL&strategies=turtle_breakout` returns a latest
  new-high research signal with lookback metadata and provider source metadata.
- Good: a flat or insufficient series returns diagnostics instead of a fabricated signal.
- Base: multiple symbols can partially succeed; provider failures for one symbol do not block
  other symbols.
- Good: `/strategies/evaluate?symbol=AAPL&strategies=volume_price_breakout&forward_windows=1,5`
  returns sample size, snapshots, per-window metrics, diagnostics, provider metadata, and
  `research_signal_only=true`.
- Base: no historical strategy snapshots returns `no_signals`, not fabricated performance.
- Bad: a strategy match is rendered as a buy recommendation, executable order, or historical
  performance claim.
- Bad: historical evaluation is described as a production backtest or validated strategy.
- Bad: InStock's strategy files are imported directly, bringing TA-Lib, database, scheduler, or
  trading dependencies into this app.

### 6. Tests Required

- Service tests assert each supported rule, diagnostics for unknown/insufficient/no-data inputs,
  and `research_signal_only=true`.
- API tests assert market-data service usage, symbol dedupe, date validation, provider-failure
  diagnostics, provider metadata, and no live provider network access.
- Service tests assert historical evaluation metrics, return-distribution diagnostics,
  benchmark-relative return, unknown strategy diagnostics, invalid window diagnostics,
  insufficient-history behavior, no-signal behavior, and `research_signal_only=true`.
- API tests assert `/strategies/evaluate` normalizes symbols, parses windows before provider access,
  fetches optional benchmark bars, returns provider metadata, and maps provider failures to HTTP 502.
- Focused validation should include strategy service/API tests, ruff on touched Python files, and
  `git diff --check`.

### 7. Wrong vs Correct

#### Wrong

```python
return {"strategy": "turtle_breakout", "action": "buy", "shares": 100}
```

This turns screening into broker-oriented trading intent.

#### Correct

```python
return {
    "code": "turtle_breakout",
    "research_signal_only": True,
    "data": {"lookback_bars": 60},
}
```

This keeps the rule explainable while preserving the no-trading boundary.

#### Wrong

```python
return {"strategy": "volume_price_breakout", "expected_return": 12.0, "action": "buy"}
```

This overclaims historical diagnostics as an executable trading recommendation.

#### Correct

```python
return {
    "status": "ok",
    "research_signal_only": True,
    "metrics": {"volume_price_breakout": {"windows": {"1": {"sample_size": 3}}}},
}
```

This keeps historical evaluation bounded by visible sample size and no-advice language.
