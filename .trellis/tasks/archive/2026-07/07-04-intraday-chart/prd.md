# Intraday Chart

## Goal

Add intraday minute chart with previous close, average price, volume, hover details, and graceful fallback.

## Requirements

- Add an intraday chart experience for instrument detail pages.
- Define a minute-data payload contract that can work with real provider data or an explicit unavailable/degraded fallback.
- Show intraday price, previous close reference, average price line, and intraday volume where data is available.
- Provide hover details for intraday points.
- Avoid silently fabricating live intraday data when provider support is unavailable.

## Acceptance Criteria

- [x] A documented intraday payload shape is available to frontend and backend code.
- [x] Instrument detail page can show an intraday chart or a clear unavailable/degraded state.
- [x] Previous close, average price, and volume are displayed when supported by the payload.
- [x] Focused tests cover available and unavailable intraday states.

## Completion Status

The intraday chart MVP is complete. The backend exposes a degraded-safe intraday payload contract, the instrument detail page treats intraday data as a non-fatal enhancement, and the frontend renders previous close, average price, volume, available data, and degraded/unavailable states.

Focused validation passed in the downstream real-intraday/cache governance checks:

```powershell
python -m pytest tests/providers/test_yfinance_provider.py tests/services/test_market_data_service.py tests/api/test_market_data_intraday_api.py tests/scripts/test_provider_readiness.py -q
# 61 passed

npx vitest run "apps/web/app/api/instruments/[symbol]/route.test.ts" "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx" "apps/web/components/intraday-price-chart.test.tsx" --reporter=dot
# 3 test files passed, 15 tests passed
```

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
