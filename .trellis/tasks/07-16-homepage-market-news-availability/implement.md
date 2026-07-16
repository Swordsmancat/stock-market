# Homepage market and news availability execution plan

## 1. Reject invalid daily rows

- Add one provider regression with a valid row followed by non-finite OHLC.
- Run it red, then make daily-bar parsing reuse the finite parser and skip the
  invalid row.
- Run provider and market-data regressions green.

## 2. Prevent contradictory cache amplification

- Add cache tests for contradictory `ok/latest.close=null`, valid `ok`, and
  explicit no-data results with an injected fake Redis client.
- Run the contradictory case red, then add the smallest result-validity guard
  before `redis.set`.
- Keep cache reads, key format, and TTL unchanged.

## 3. Keep stored news responsive

- Add an ASGI concurrency regression that starts a deliberately slow dashboard
  service call and asserts `/news/latest` finishes before it.
- Run it red against the async dashboard route, change the route to a sync
  function, and run it green.
- Do not change the five-second homepage timeout.

## 4. Add bounded CN-index fallback

- Add provider tests for exchange-prefix mapping, date filtering, finite-row
  normalization, and provider failure propagation for Sina index daily data.
- Add service tests proving valid yfinance data makes zero Sina calls, empty or
  invalid yfinance data makes exactly one call, and fallback success uses one
  coherent source with truthful attribution.
- Add empty/failure regressions that preserve explicit no-data/unavailable
  without retrying, writing rows, or affecting non-CN indices.
- Implement the smallest dedicated AkShare index method and dashboard decision
  boundary; leave the stock coordinator and thresholds unchanged.

## 5. Validate and accept

```powershell
python -m pytest -q tests/providers/test_yfinance_provider.py
python -m pytest -q tests/providers/test_cn_market_providers.py
python -m pytest -q tests/api/test_dashboard_api.py tests/api/test_news_api.py
python -m pytest -q tests/services/test_market_dashboard_service.py tests/services/test_market_data_service.py
python -m ruff check packages/providers/yfinance_provider.py packages/shared/cache.py apps/api/routers/dashboard.py tests/providers/test_yfinance_provider.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py
npm run test:web -- --run apps/web/app/[locale]/page.test.tsx
npx tsc --noEmit -p apps/web/tsconfig.json
python ./.trellis/scripts/task.py validate 07-16-homepage-market-news-availability
git diff --check
```

- Run relevant full regression groups after focused checks.
- Reload the API process, clear only market-overview cache keys, and verify Web
  3000/API 8000 health plus the homepage/browser repro.

## 6. Restore Docker Desktop full-stack startup

- Add the normal web service to `docker-compose.yml` with container/host API
  addresses and host port 3000.
- Add health-gated dependencies and restart policies for the default stack.
- Update quick-start and local-development commands to document one-command
  full-stack startup while retaining host-side development instructions.
- Validate the resolved Compose model, build/start the normal API and web, and
  probe `/health` plus `/zh` from the host.

## 7. Finish

- Update backend executable specs with the finite-row, cacheability, sync-route,
  and bounded CN-index fallback contracts.
- Commit only task-owned files, archive the task, record the journal, and push.
- Leave macro-source completion as a separate product task.
