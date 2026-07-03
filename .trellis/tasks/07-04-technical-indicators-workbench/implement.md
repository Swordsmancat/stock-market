# Technical Indicators Workbench Implementation Plan

## Slice 1: Backend Indicator Contract

1. Add `calculate_kdj` to `packages/analytics/indicators.py`.
2. Add focused analytics tests for MACD and KDJ.
3. Extend `packages/services/indicators.py` with latest MACD/KDJ helpers.
4. Persist `macd` and `kdj` alongside existing daily indicators.
5. Refresh all known daily technical indicator codes before re-writing latest rows.
6. Update service and API tests to expect the expanded six-indicator payload.
7. Run:
   - `python -m pytest tests/analytics/test_indicators.py tests/services/test_indicator_persistence_service.py tests/api/test_indicators_db_api.py`

## Slice 2: Frontend Indicator Workbench

1. Extend or introduce frontend indicator calculation helpers.
2. Add chart controls for MA, BOLL, Volume, MACD, RSI, and KDJ.
3. Localize user-visible labels in English and Chinese.
4. Add focused chart helper/component tests.
5. Run `npm run test:web`.

## Commit Policy

Commit and push each passing slice separately. Do not include unrelated working tree noise.
