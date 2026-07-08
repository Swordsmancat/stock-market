# News Source Configuration And Adapter MVP - Implement

## Ordered Checklist

- [x] Resolve Q2: first provider adapters are Anspire AI Search and SerpAPI Baidu.
- [x] Before coding, load `trellis-before-dev` and re-read `prd.md`, `design.md`, `implement.md`, plus relevant backend/frontend specs.
- [x] Add backend provider registry:
  - provider ids and capabilities;
  - implementation status;
  - credential requirements;
  - readiness/citation caveats.
- [x] Extend backend platform settings:
  - enabled provider list;
  - provider order;
  - provider key storage with secret preservation;
  - public configured flags and capabilities.
- [x] Mirror needed settings fields in `apps/web/lib/platform-settings-store.ts` if the web app needs to edit them in the first slice.
- [x] Add normalized news search candidate contract and adapter base helpers.
- [x] Implement Anspire AI Search and SerpAPI Baidu adapters with mocked tests only.
- [x] Add fallback orchestration:
  - disabled provider;
  - missing credentials;
  - timeout;
  - provider error;
  - invalid/empty response;
  - database fallback.
- [x] Reuse `NewsArticle` and `SentimentSignal` for persisted articles unless metadata needs force a migration.
- [x] Add or update API route(s) for news search/ingest if needed.
- [x] Add Settings UI provider controls only if backend settings are exposed for editing in this slice.
- [x] Update English and Chinese messages for any new UI text.
- [x] Update docs/runbook for provider keys, quota, citation boundary, and fallback behavior.
- [x] Run focused backend tests.
- [x] Run focused frontend tests if UI changes.
- [x] Run type/lint/test commands required by touched packages.

## Validation Commands

Initial expected commands, to be refined after implementation:

```powershell
pytest tests/services/test_news_service.py tests/api/test_news_api.py
pytest tests/services/test_information_sources_service.py
npm run test:web -- --reporter=dot
npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0
git diff --check
```

## Risky Files And Rollback Points

- `packages/services/platform_settings.py`: must preserve existing LLM/Tushare secrets.
- `apps/web/lib/platform-settings-store.ts`: must mirror backend settings carefully if changed.
- `packages/services/news.py`: existing mock/yfinance/AkShare behavior must not regress.
- `apps/api/routers/news.py`: existing `/news/mock-ingest` and `/news/{symbol}` tests must keep passing.
- `packages/domain/models.py` and Alembic migrations: only change if metadata cannot be represented otherwise.
- `apps/web/app/[locale]/settings/page.tsx`: settings form is already broad; avoid breaking existing provider and macro/index settings.

## Follow-Up Order After First Slice

1. Social sentiment evidence boundary and adapter design.
2. InStock technical indicators or K-line pattern recognition.
3. InStock strategy screening and backtest validation.
4. Automatic trading safety foundation, paper-trading first.
