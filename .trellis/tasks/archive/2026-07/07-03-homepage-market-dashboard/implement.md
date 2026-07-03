# Homepage market dashboard implementation plan

## Ordered checklist

1. Load execution context
   - Read Trellis workflow/spec context for backend, frontend, and cross-layer work.
   - Start the task before editing product code.

2. Backend market indicator storage
   - Add `MarketIndicator` and `MarketIndicatorObservation` to `packages/domain/models.py`.
   - Add an Alembic migration for the new tables and unique constraints.
   - Implement `packages/services/market_indicators.py` with indicator definition upsert, observation upsert, seed loading, and latest-observation payload helpers.
   - Add focused service tests for seed/upsert/read/no-data behavior.

3. Default index catalog and dashboard aggregation
   - Add a code-owned CN/HK/US default index catalog with internal codes and provider-symbol maps.
   - Implement `packages/services/market_dashboard.py` to assemble followed instruments, index summaries, valuation indicators, diagnostics, and range metadata.
   - Ensure item-level failures return `unavailable` diagnostics without failing the full response.

4. Dashboard API
   - Add `apps/api/routers/dashboard.py` with `GET /dashboard/market-overview?provider=...`.
   - Register the router in `apps/api/main.py`.
   - Add focused API tests for successful payload shape and partial no-data behavior.

5. Frontend compact K-line chart
   - Add `apps/web/components/compact-candlestick-chart.tsx`.
   - Reuse `deriveOhlcBar` and `buildChartPoints`.
   - Render compact candles, MA20, and volume; render a provided empty message when no bars are available.

6. Homepage market-dashboard layout
   - Update `apps/web/app/[locale]/page.tsx` to fetch `/dashboard/market-overview`.
   - Put core indices, followed K-line cards, and valuation cards before existing operational sections.
   - Keep existing data-health/task/report/news/portfolio content lower on the page where possible.
   - Preserve explicit daily-bar wording and text-first movement semantics.

7. Localization
   - Add English and Chinese strings for market overview, index cards, K-line cards, Buffett Indicator, no-data states, and recovery actions.

8. Tests and validation
   - Update `apps/web/app/[locale]/page.test.tsx` for the new homepage hierarchy and no-data branches.
   - Run focused backend tests for the new services/API.
   - Run focused frontend homepage tests.
   - Run Trellis validation.

9. Finish workflow
   - Commit and push implementation after validation.
   - Archive the Trellis task and push the archive commit.
   - List remaining active tasks.

## Validation commands

```bash
pytest tests/services/test_market_indicators_service.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py
npm run test:web -- "apps/web/app/[locale]/page.test.tsx"
python ./.trellis/scripts/task.py validate .trellis/tasks/07-03-homepage-market-dashboard
```

## Risky files and rollback points

- `packages/domain/models.py` and Alembic migration: additive only; rollback is dropping the new tables if needed.
- `packages/services/market_dashboard.py`: isolate new aggregation logic so existing market-data/watchlist flows remain unchanged.
- `apps/web/app/[locale]/page.tsx`: large layout change; keep existing lower-page diagnostics available to reduce regression risk.
- `apps/web/components/compact-candlestick-chart.tsx`: new component; avoid changing existing `PriceChart` unless absolutely necessary.

## Review gates before `task.py start`

- `prd.md` has converged and contains no resolved open questions.
- `design.md` defines the backend/frontend/API boundaries.
- `implement.md` defines validation commands and rollback points.
