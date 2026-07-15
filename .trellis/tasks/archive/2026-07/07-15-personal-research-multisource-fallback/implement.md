# Automatic multi-source data and news fallback execution plan

## 1. Lock contracts and tests

- Update the personal-research, intraday-cache, and news-search contracts with
  the approved automatic fallback and crawler/Cookie boundaries.
- Add failing focused tests for daily mixed-provenance recovery, intraday
  market forwarding/fallback, news DB-first sequential refresh, and frontend
  one-shot behavior before changing implementations.

## 2. Recover complete daily series

- Extend `DailyBarFetchCoordinator` with optional coverage validation while
  preserving existing callers and attempt redaction.
- Change mixed-database handling to request one complete remote series and fall
  back to the existing degraded database cohort if recovery fails.
- Preserve latest/indicator/assistant provenance and no-write GET behavior.

## 3. Add market-aware intraday fallback

- Add `market` to API/service/frontend intraday signatures.
- Implement and unit-test AkShare Eastmoney and Sina minute normalization with
  Asia/Shanghai timestamps.
- Add sequential CN intraday coordination, validation, source attempts, and
  exact no-data/degraded semantics.
- Keep session-policy shortcuts and cache-hit behavior; prevent conflicting
  provider cache metadata.

## 4. Add sequential news refresh

- Implement non-writing yfinance and AkShare news candidate adapters with exact
  market identity and sanitized failures.
- Add DB-first, stop-on-first-persisted-success refresh service and bounded
  global latest stored-news query.
- Add FastAPI refresh/latest routes. Keep existing read/search/search-ingest
  routes compatible and stored-news-only AI citation behavior unchanged.
- Keep Tushare, mock, social candidates, generic crawling, and Cookie paths out
  of production fallback.

## 5. Add frontend recovery and truthful states

- Add same-origin refresh proxy and tests.
- Add one-shot detail news recovery with session key, visible pending/result
  state, direct news projection replacement, and explicit retry.
- Forward market for intraday and preserve index exclusions.
- Switch homepage to bounded global stored news and split failed versus empty.
- Add localized diagnostic-code strings; do not render raw backend messages.

## 6. Validate

Focused backend:

```powershell
python -m pytest -q tests/services/test_daily_bar_sources.py tests/services/test_market_data_service.py tests/providers/test_cn_market_providers.py tests/services/test_news_service.py
python -m pytest -q tests/api/test_market_data_api.py tests/api/test_market_data_intraday_api.py tests/api/test_news_api.py tests/ai/test_market_assistant.py
python -m ruff check packages/services/daily_bar_sources.py packages/services/market_data.py packages/services/news.py packages/services/news_search.py packages/providers/akshare_provider.py apps/api/routers/market_data.py apps/api/routers/news.py
```

Focused frontend:

```powershell
npm --prefix apps/web test -- --run apps/web/lib/instrument-detail.test.ts apps/web/components/instrument-detail-client.test.tsx apps/web/app/api/news apps/web/app/[locale]/page.test.tsx
npm --prefix apps/web exec tsc -- --noEmit
```

Full gates:

```powershell
python -m pytest -q
npm run test:web
npm --prefix apps/web exec tsc -- --noEmit
python -m ruff check <touched-python-files>
python ./.trellis/scripts/task.py validate 07-15-personal-research-multisource-fallback
git diff --check
```

- Parse both locale JSON files.
- Run a production Web build in isolation.
- Run secret/cookie/raw-response scans over touched files and task artifacts.

## 7. Deploy and deliver

- Verify current normal Web/API health and record process identities without
  exposing command lines or environment values.
- Reload only normal Web/API after validation; choose unused ports for any
  pre-deploy acceptance stack.
- Verify one no-local-bar CN symbol, one mixed-provenance symbol, one intraday
  fallback symbol, one news recovery success, one all-empty news result, and
  homepage aggregate news on desktop/mobile.
- Reconfirm PostgreSQL, Redis, Worker, Beat, and five-day acceptance artifacts
  were not reset or staged.
- Run Trellis Check and finish flow, commit/push explicit task-owned and source
  files, archive this task, then restore the five-day acceptance task context.

## Completion evidence

- Full Python suite: 980 passed.
- Full Web suite: 94 files and 352 tests passed; TypeScript and locale JSON
  validation passed.
- Ruff, Alembic head/current, Trellis validation, redaction scan, and
  `git diff --check` passed.
- The isolated webpack production build compiled and generated all 41 static
  pages. The default Next 16 Turbopack path still reproduces the framework-level
  `/_global-error` `workStore` failure; this does not affect the successful
  webpack build or the validated normal development runtime.
