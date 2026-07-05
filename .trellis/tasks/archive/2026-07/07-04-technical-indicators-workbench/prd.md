# Technical Indicators Workbench

## Goal

Complete MACD RSI KDJ BOLL indicator library integration and configurable chart display.

## Requirements

- Complete the technical indicator library around the existing analytics, service, API, and chart foundations.
- Support MACD, RSI, KDJ, BOLL, and moving averages in a user-facing indicator workbench.
- Preserve current daily-bar indicator persistence while adding missing MACD/KDJ calculations where needed.
- Expose configurable display controls for multiple indicators without overloading the main price chart.
- Localize all user-facing labels in English and Chinese.

## Acceptance Criteria

- [x] MACD and KDJ calculations have focused automated tests.
- [x] Stored/API indicator payloads include the newly supported indicators or explicitly document why they are computed client-side only.
- [x] Instrument detail UI can add/remove supported indicators.
- [x] Indicator parameters are configurable for at least common defaults without breaking existing MA/RSI/BOLL behavior.
- [x] Relevant pytest and web tests pass.

## Completion Status

The technical indicator workbench MVP is complete. Backend analytics and persistence now cover the expanded indicator set, and the frontend advanced candlestick chart exposes localized controls and chart series for MA, BOLL, Volume, MACD, RSI, and KDJ with configurable defaults.

Focused validation passed:

```powershell
python -m pytest tests/analytics/test_indicators.py tests/services/test_indicator_persistence_service.py tests/api/test_indicators_db_api.py -q
# 9 passed

npx vitest run "apps/web/lib/chart-indicators.test.ts" "apps/web/components/advanced-candlestick-chart.test.tsx" --reporter=dot
# 2 test files passed, 14 tests passed
```

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
