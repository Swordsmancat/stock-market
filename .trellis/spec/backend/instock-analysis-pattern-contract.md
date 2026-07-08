# InStock-Inspired Analysis Pattern Contract

## Scenario: Stored Chip Distribution Research Signal

### 1. Scope / Trigger

- Trigger: `calculate_and_store_daily_indicators(...)` stores an additive
  `chip_distribution` technical indicator inspired by the `myhhub/stock` CYQ
  / chip-distribution capability.
- Scope: pure analytics under `packages/analytics/chip_distribution.py`,
  persisted indicator assembly in `packages/services/indicators.py`,
  `/indicators/recalculate`, `/indicators/{symbol}`, and stored technical
  indicator consumers.
- Non-goals: importing InStock's K-line UI, using scraped chip-race endpoints,
  adding free-float share crawlers, TA-Lib, MySQL/Tornado dependencies,
  strategy execution, or automatic trading.

### 2. Signatures

- Pure helper:
  `calculate_latest_chip_distribution(open_prices, high_prices, low_prices, close_prices, volumes, lookback_days=210, bucket_count=60) -> dict[str, object]`
- Stored technical indicator row:
  - `TechnicalIndicator.indicator_code = "chip_distribution"`
  - `TechnicalIndicator.timeframe = "1d"`
  - `TechnicalIndicator.as_of = latest daily bar at UTC midnight`
  - `TechnicalIndicator.params.rule_set = "chip_distribution_v1"`
  - `TechnicalIndicator.params.research_signal_only = true`
  - `TechnicalIndicator.params.approximation = "volume_weighted_without_float_shares"`
- Stored/API value shape includes:
  - `rule_set = "chip_distribution_v1"`
  - `integration_source = "instock_inspired_cyq"`
  - `status`
  - `research_signal_only`
  - `approximation`
  - `lookback_days`, `evaluated_bars`, `bucket_count`
  - `benefit_ratio`
  - `avg_cost` and `weighted_average_cost`
  - `cost_ranges["70"]` and `cost_ranges["90"]`
  - `top_buckets` and `buckets`
  - `limitations`

### 3. Contracts

- The helper must remain pure Python/pandas over local daily OHLCV bars.
- Because the project currently stores volume but not free-float shares or true
  turnover rate, the first CYQ slice is a volume-normalized research
  approximation. It must say so in both params and value payloads.
- Payloads are research signals only. They must not emit buy/sell/hold actions,
  target prices, position sizes, order intents, or execution instructions.
- Stored `TechnicalIndicator` rows remain the citation boundary. A live
  calculation, InStock README/source line, or source-readiness note is not an
  assistant citation until stored locally.
- The implementation may acknowledge `myhhub/stock` as an Apache-2.0
  inspiration, but must not vendor the repository or import its runtime modules.

### 4. Validation & Error Matrix

- Empty OHLCV/volume series -> payload `status="no_data"`, empty buckets, and no
  fabricated cost metrics.
- Zero or missing volume for all rows -> payload `status="no_data"`.
- Non-positive `lookback_days` -> payload `status="invalid_input"` and no cost
  metrics.
- Flat prices with positive volume may be represented as one bucket.
- Existing numeric indicators and `candlestick_patterns` must remain additive
  and unchanged except for the total refreshed indicator count.
- Stored payloads must preserve nested dicts, lists, booleans, strings, and nulls
  through `get_stored_indicators_payload(...)`.

### 5. Good/Base/Bad Cases

- Good: a stored `chip_distribution` payload includes 70% and 90% cost ranges,
  benefit ratio, top buckets, explicit limitations, and
  `research_signal_only=true`.
- Good: no volume returns a no-data payload rather than a fake cost band.
- Base: assistant/report consumers may cite the stored technical-indicator row
  and describe it as a volume-normalized CYQ approximation.
- Bad: the payload claims provider-grade chip concentration without reviewed
  free-float/turnover inputs.
- Bad: a low average cost becomes a buy recommendation or order intent.
- Bad: InStock's JS/Python CYQ runtime, web UI, crawler, or database stack is
  imported wholesale.

### 6. Tests Required

- Analytics tests assert evaluated and no-data CYQ payloads, approximation
  metadata, cost ranges, bucket counts, and `research_signal_only=true`.
- Service tests assert `calculate_and_store_daily_indicators(...)` writes
  `chip_distribution` alongside existing indicators without changing previous
  numeric values.
- API tests assert `/indicators/recalculate` and `/indicators/{symbol}` expose
  the additive nested payload and preserve old fields.
- Focused validation should include indicator analytics/service/API tests, ruff
  on touched Python files, and `git diff --check`.

## Scenario: Stored Candlestick Pattern Research Signal

### 1. Scope / Trigger

- Trigger: `calculate_and_store_daily_indicators(...)` stores an additive
  `candlestick_patterns` technical indicator inspired by the `myhhub/stock`
  K-line pattern-recognition capability.
- Scope: pure analytics under `packages/analytics/`, persisted indicator assembly in
  `packages/services/indicators.py`, `/indicators/recalculate`, `/indicators/{symbol}`,
  and consumers that cite stored `technical_indicators:*` evidence.
- Non-goals: TA-Lib dependency installation, copying InStock's MySQL/Tornado job stack,
  proxy/cookie crawling, strategy execution, backtest claims, or automatic trading.

### 2. Signatures

- Pure helper:
  `detect_latest_candlestick_patterns(open_prices, high_prices, low_prices, close_prices) -> dict[str, object]`
- Stored technical indicator row:
  - `TechnicalIndicator.indicator_code = "candlestick_patterns"`
  - `TechnicalIndicator.timeframe = "1d"`
  - `TechnicalIndicator.as_of = latest daily bar at UTC midnight`
  - `TechnicalIndicator.params.rule_set = "candlestick_patterns_v1"`
  - `TechnicalIndicator.params.research_signal_only = true`
- Stored/API value shape:

```json
{
  "rule_set": "candlestick_patterns_v1",
  "integration_source": "instock_inspired_rules",
  "status": "evaluated",
  "research_signal_only": true,
  "evaluated_bars": 20,
  "pattern_count": 1,
  "patterns": [
    {
      "code": "hammer",
      "label": "Hammer",
      "market_bias": "bullish",
      "lookback_bars": 1,
      "rule_set": "candlestick_patterns_v1"
    }
  ]
}
```

### 3. Contracts

- The first slice detects only deterministic, no-dependency patterns:
  `bullish_engulfing`, `bearish_engulfing`, `hammer`, `shooting_star`, and `doji`.
- The helper evaluates the latest bar and, for engulfing patterns, the immediately previous bar.
- Pattern payloads are research signals only. They must not emit buy/sell/hold actions,
  target prices, position sizes, order intents, or execution instructions.
- Stored `TechnicalIndicator` rows remain the citation boundary. A live calculation or
  InStock source-readiness note is not an assistant citation until stored locally.
- Values may contain nested dictionaries and arrays. Indicator serializers must preserve
  strings, booleans, nulls, lists, and nested dicts while still converting numeric values to floats.
- The implementation may acknowledge `myhhub/stock` as an Apache-2.0 inspiration, but must not
  vendor the repository or depend on TA-Lib without a separate dependency and license review.

### 4. Validation & Error Matrix

- Empty OHLC series -> payload `status="no_data"`, `pattern_count=0`, `patterns=[]`.
- Invalid latest candle range -> payload `status="no_data"`, no fabricated pattern.
- Only one valid bar -> single-bar patterns may be detected; two-bar engulfing patterns are skipped.
- Missing or disabled database session -> existing stored-indicator no-data behavior remains.
- Insufficient bars for MA calculation -> existing `calculate_and_store_daily_indicators`
  `insufficient_data` response remains; no partial pattern-only write in this slice.
- Existing numeric indicators present -> `candlestick_patterns` is additive and must not change
  MA/RSI/Bollinger/ATR/MACD/KDJ values.

### 5. Good/Base/Bad Cases

- Good: a stored latest hammer pattern appears under
  `indicators.candlestick_patterns.patterns[]` with `research_signal_only=true`.
- Good: no latest pattern is stored as an evaluated zero-count result, not as a fake signal.
- Base: assistant/report consumers include the stored technical-indicator citation and may list
  `candlestick_patterns` as one of the indicator codes.
- Bad: a source-readiness line such as "InStock supports 61 patterns" is treated as evidence.
- Bad: a detected bullish pattern becomes a direct buy recommendation or broker order intent.
- Bad: InStock's TA-Lib/MySQL/Tornado modules are imported wholesale into this FastAPI service.

### 6. Tests Required

- Analytics tests assert each first-slice pattern code, market bias, no-data behavior, and the
  `research_signal_only` flag.
- Service tests assert `calculate_and_store_daily_indicators(...)` writes
  `candlestick_patterns` alongside existing indicators without changing previous numeric values.
- API tests assert `/indicators/recalculate` and `/indicators/{symbol}` expose the additive
  nested payload and preserve old fields.
- Full backend validation should include focused indicator tests, ruff on touched Python files,
  and `git diff --check`.

### 7. Wrong vs Correct

#### Wrong

```python
return {"action": "buy", "pattern": "hammer"}
```

This turns a chart pattern into a trading instruction.

#### Correct

```python
return {
    "research_signal_only": True,
    "patterns": [{"code": "hammer", "market_bias": "bullish"}],
}
```

This keeps the shape useful for research while preserving the no-trading boundary.
