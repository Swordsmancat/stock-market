# Public research source hardening execution plan

## 1. Lock failing contracts

- Add focused daily-bar tests for sparse coherent recovery, sufficient cohort
  reuse, non-CN exclusion, and retained-database failure behavior.
- Add provider tests for fixed Cookie-free request construction, timeout,
  redirect/status/media/size/JSONP/schema rejection, normalization, and empty.
- Update news refresh and legacy ingestion tests to require
  `eastmoney_public` and to forbid `ak.stock_news_em`.

## 2. Recover severe daily-bar sparsity

- Add the arithmetic weekday/minimum-row helper.
- Generalize the database recovery decision while preserving the existing
  mixed-provenance branch and compatibility payload.
- Add the stable database insufficiency diagnostic and retain attempts on
  remote failure.

## 3. Replace the public CN news wrapper

- Add the provider module with the exact GET/JSONP/schema boundary.
- Add the service adapter and fixed source-order integration.
- Route the legacy AkShare-named ingestion compatibility function through the
  same provider.
- Keep the existing platform switch, persistence, citations, and frontend API
  shape unchanged.

## 4. Validate

```powershell
python -m pytest -q tests/providers/test_eastmoney_public_news_provider.py
python -m pytest -q tests/services/test_daily_bar_sources.py tests/services/test_market_data_service.py
python -m pytest -q tests/services/test_news_service.py tests/services/test_cn_market_ingest.py tests/api/test_news_api.py tests/ai/test_market_assistant.py
python -m ruff check packages/providers/eastmoney_public_news.py packages/services/market_data.py packages/services/news.py packages/services/news_search.py tests/providers/test_eastmoney_public_news_provider.py tests/services/test_market_data_service.py tests/services/test_news_service.py tests/services/test_cn_market_ingest.py tests/api/test_news_api.py
python ./.trellis/scripts/task.py validate 07-16-public-research-source-hardening
git diff --check
```

- Run a bounded Cookie-free provider GET for one exact CN symbol after injected
  tests pass; record only safe status/count/provider metadata.
- Recheck normal Web/API health and confirm no unrelated dirty path was staged,
  reverted, or modified.

## 5. Finish

- Run Trellis Check against the final diff and update executable specs if the
  source contract changed.
- Commit only task-owned source/tests/specs and task artifacts when requested;
  leave the five-day acceptance progress and unrelated worktree changes alone.
- Record the fundamental-nullability/provider rollout as the next separate
  correctness task; do not lower readiness thresholds as a shortcut.
