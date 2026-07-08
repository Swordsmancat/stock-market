# Recommendation Signal Evaluation Contract

## Scenario: Public Historical Signal Evaluation API

### 1. Scope / Trigger

- Trigger: `GET /recommendations/evaluate` exposes the existing deterministic
  `evaluate_recommendation_signals(...)` service through a thin FastAPI route.
- Scope: API parsing in `apps/api/routers/recommendations.py`, historical bar loading
  through `packages/services/market_data.py`, signal metrics in
  `packages/services/smart_recommendations.py`, and focused API/service tests.
- Non-goals: persistent signal-history tables, scheduled evaluation, transaction costs,
  slippage, portfolio simulation, parameter optimization, brokerage execution, or live
  trading recommendations.

### 2. Signatures

- API:
  `GET /recommendations/evaluate?symbol=AAPL&start=YYYY-MM-DD&end=YYYY-MM-DD`
- Optional query fields:
  - `signal_types`: comma-separated values from `breakout`, `volume_anomaly`,
    `oversold_rebound`, `strong_momentum`.
  - `forward_windows`: comma-separated positive integer forward windows in bars.
  - `benchmark_symbol`: optional symbol fetched over the same date window for relative returns.
  - `provider`: optional market-data provider name.
- Service entry:
  `evaluate_recommendation_signals(symbol, bars, signal_types=None, forward_windows=None, benchmark_bars=None)`

### 3. Contracts

- The API reads historical daily bars via `get_bars_payload(...)`; it does not write to the database.
- `start` must be on or before `end`.
- `symbol` is trimmed and uppercased; empty symbols are rejected.
- `forward_windows` is parsed before provider access. Non-integer values return HTTP 400.
- Invalid signal types are ignored by the service and fall back to the default signal list if none remain.
- The response preserves the service payload and adds source metadata:
  `generated_at`, `source`, `provider`, `requested_provider`, `effective_provider`,
  `benchmark_symbol`, and `research_signal_only=true`.
- The response must keep the service disclaimer:
  `Historical signal evaluation is a research aid only and is not investment advice.`
- Current `/recommendations` output remains an unbacktested research-candidate list and includes
  `research_signal_only=true`; it must not imply order execution readiness.

### 4. Validation & Error Matrix

- `start > end` -> HTTP 400.
- Empty `symbol` -> HTTP 400.
- `forward_windows` contains a non-integer -> HTTP 400 before provider access.
- Provider boundary raises `MarketDataProviderError` -> HTTP 502 with provider/category only.
- Provider boundary raises `ValueError` -> HTTP 400.
- No bars or fewer than 30 bars -> service payload `status="no_data"` with
  `NOT_ENOUGH_HISTORICAL_BARS`.
- No matching historical signal snapshots -> service payload `status="no_signals"` with
  `NO_SIGNAL_SNAPSHOTS`.
- Missing benchmark bars -> diagnostic such as `BENCHMARK_UNAVAILABLE`; never encode missing
  benchmark-relative return as zero.

### 5. Good/Base/Bad Cases

- Good: `/recommendations/evaluate` returns sample size, per-window hit rate, forward return,
  max drawdown, benchmark-relative return when available, diagnostics, and a non-advice disclaimer.
- Base: the endpoint returns `no_data` or `no_signals` instead of fabricating metrics.
- Base: `/recommendations` still returns live research candidates for UI cards, while
  `/recommendations/evaluate` returns historical outcome diagnostics.
- Bad: historical evaluation is described as a trading strategy backtest with fill prices,
  transaction costs, or executable orders.
- Bad: a realtime candidate from `/recommendations` is treated as validated because a separate
  historical evaluation endpoint exists.

### 6. Tests Required

- API tests assert `/recommendations/evaluate` normalizes symbols, calls market-data service once
  per evaluated symbol/benchmark, returns metrics, source metadata, and `research_signal_only=true`.
- API tests assert invalid `forward_windows` returns HTTP 400 before provider work.
- Service tests assert each signal type has deterministic forward metrics and diagnostics for
  insufficient history, no signals, invalid windows, insufficient post-signal bars, and missing benchmark.
- Recommendation API tests should keep `/recommendations` additive and backward compatible.

### 7. Wrong vs Correct

#### Wrong

```python
return {"strategy": "breakout", "action": "buy", "expected_return": 12.0}
```

This turns historical diagnostics into a trading instruction and overclaims future return.

#### Correct

```python
return {
    "status": "ok",
    "research_signal_only": True,
    "metrics": {"breakout": {"windows": {"5": {"sample_size": 3}}}},
    "disclaimer": "Historical signal evaluation is a research aid only and is not investment advice.",
}
```

This presents historical evaluation as bounded research evidence with visible sample size.
