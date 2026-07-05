# Technical Indicators Workbench Design

## Boundaries

This task completes the technical indicator foundation and exposes a user-facing workbench in slices.

The first implementation slice is backend-focused:

- Add KDJ analytics calculation.
- Add focused MACD and KDJ analytics tests.
- Persist MACD and KDJ through the existing daily indicator service.
- Expose MACD and KDJ through the existing `/indicators/{symbol}` payload.

Frontend chart controls are a follow-up slice in the same task after the backend payload contract is stable.

## Backend Contract

The existing `TechnicalIndicator.value_json` field remains the storage contract. No database migration is required.

New indicator payloads use nested values, matching the existing `bollinger` contract:

```json
{
  "macd": {
    "macd": 0.0,
    "signal": 0.0,
    "histogram": 0.0
  },
  "kdj": {
    "k": 50.0,
    "d": 50.0,
    "j": 50.0
  }
}
```

## KDJ Formula

Use the common KDJ formula:

- `RSV = (close - lowest_low) / (highest_high - lowest_low) * 100`.
- `K = previousK * 2 / 3 + RSV / 3`.
- `D = previousD * 2 / 3 + K / 3`.
- `J = 3 * K - 2 * D`.
- Initial K and D are `50.0`.
- If `highest_high == lowest_low`, RSV is `50.0` to avoid divide-by-zero.

## Compatibility

- Existing MA, RSI, Bollinger, and ATR behavior must remain unchanged.
- The `/indicators/recalculate` route remains the entry point.
- The `/indicators/{symbol}` route continues to return a single `indicators` object and simply gains `macd` and `kdj` keys when available.

## Testing

- Formula tests live in `tests/analytics/test_indicators.py`.
- Persistence tests live in `tests/services/test_indicator_persistence_service.py`.
- API payload tests live in `tests/api/test_indicators_db_api.py`.
