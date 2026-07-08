# InStock-Inspired Strategy Screening Contract

## Scenario: Research-Only Strategy Screening

### 1. Scope / Trigger

- Trigger: `GET /strategies/screen` evaluates the latest daily OHLCV window against
  deterministic, InStock-inspired screening rules.
- Scope: API parsing in `apps/api/routers/strategy_screening.py`, market-data loading
  through `packages/services/market_data.py`, pure screening logic in
  `packages/services/strategy_screening.py`, and focused API/service tests.
- Non-goals: persisted strategy history, portfolio backtests, parameter optimization,
  broker order intents, automatic trading, TA-Lib installation, or vendoring
  `myhhub/stock`.

### 2. Signatures

- API:
  `GET /strategies/screen?symbols=AAPL,MSFT`
- Optional query fields:
  - `strategies`: comma-separated strategy codes from `volume_price_breakout`,
    `turtle_breakout`, and `ma_trend_up`.
  - `start` / `end`: optional historical bar window. If omitted, the API uses a
    365-day lookback ending today.
  - `provider`: optional market-data provider name.
  - `limit`: flattened match limit, bounded by the API route.
- Service entry:
  `screen_latest_instock_strategies(symbol, bars, strategy_codes=None)`

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
- API diagnostics expose provider/category and rule diagnostics only. They must not expose
  provider credentials or raw provider payloads.
- Strategy screening results are collection/analysis outputs, not stored citations. They become
  assistant-citable only if a future slice stores reviewed evidence rows with a stable citation path.

### 4. Validation & Error Matrix

- Empty `symbols` -> HTTP 400.
- `start > end` -> HTTP 400 before provider access.
- Provider boundary raises `MarketDataProviderError` -> route-level diagnostic with no exception.
- Provider boundary raises `ValueError` -> route-level invalid-request diagnostic.
- No valid bars -> service payload `status="no_data"` with `NO_BARS`.
- Unknown strategy codes -> `UNKNOWN_STRATEGY_CODE` diagnostic and ignored.
- Not enough bars for a requested strategy -> `INSUFFICIENT_BARS` diagnostic.
- Enough bars but no strategy match -> `status="no_match"` with `NO_STRATEGY_MATCH`.
- At least one rule matches -> `status="matched"` and `matches[]`.

### 5. Good/Base/Bad Cases

- Good: `/strategies/screen?symbols=AAPL&strategies=turtle_breakout` returns a latest
  new-high research signal with lookback metadata and provider source metadata.
- Good: a flat or insufficient series returns diagnostics instead of a fabricated signal.
- Base: multiple symbols can partially succeed; provider failures for one symbol do not block
  other symbols.
- Bad: a strategy match is rendered as a buy recommendation, executable order, or historical
  performance claim.
- Bad: InStock's strategy files are imported directly, bringing TA-Lib, database, scheduler, or
  trading dependencies into this app.

### 6. Tests Required

- Service tests assert each supported rule, diagnostics for unknown/insufficient/no-data inputs,
  and `research_signal_only=true`.
- API tests assert market-data service usage, symbol dedupe, date validation, provider-failure
  diagnostics, provider metadata, and no live provider network access.
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
