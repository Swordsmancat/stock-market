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

## InStock K-Line Pattern Slice

- [x] Confirm InStock pattern recognition is TA-Lib/job-stack based and should not be imported wholesale.
- [x] Add pure Python/pandas latest-candle pattern detection for a small deterministic MVP.
- [x] Persist `candlestick_patterns` through the existing `TechnicalIndicator` table.
- [x] Preserve existing numeric indicator outputs and stored technical-indicator citation boundary.
- [x] Add focused analytics, service, and API tests.
- [x] Add runbook/spec coverage for Apache-2.0 attribution, payload shape, and no-trading rules.
- [x] Run final focused checks and diff whitespace checks before commit.

## Recommendation Signal Evaluation API Slice

- [x] Reuse the existing deterministic `evaluate_recommendation_signals` service instead of copying InStock backtest modules.
- [x] Add `GET /recommendations/evaluate` with symbol/date/provider/signal/window/benchmark query parameters.
- [x] Preserve the research-only disclaimer and add `research_signal_only=true`.
- [x] Keep provider failures sanitized and avoid database writes.
- [x] Add API tests for successful metrics and invalid forward-window validation.
- [x] Add code-spec/runbook coverage for the public API contract and no-trading boundary.

## InStock Strategy Screening API Slice

- [x] Add pure Python InStock-inspired strategy screening rules without importing TA-Lib or InStock runtime modules.
- [x] Support `volume_price_breakout`, `turtle_breakout`, and `ma_trend_up` as research-only signals.
- [x] Add `GET /strategies/screen` with multi-symbol, strategy-filter, date-window, provider, and limit query parameters.
- [x] Preserve sanitized provider diagnostics and partial success across symbols.
- [x] Keep results non-persistent and explicitly out of assistant citation/trading boundaries.
- [x] Add focused service/API tests and backend spec/runbook coverage.

## InStock Strategy Evaluation API Slice

- [x] Reuse the strategy screening rules to scan historical strategy snapshots.
- [x] Add `evaluate_instock_strategy_signals` with sample size, forward-return, hit-rate, drawdown, benchmark-relative, and diagnostics payloads.
- [x] Add `GET /strategies/evaluate` with symbol/date/provider/strategy/window/benchmark query parameters.
- [x] Preserve the research-only disclaimer and add `research_signal_only=true`.
- [x] Keep provider failures sanitized and avoid database writes, persistence, order intents, or transaction-cost assumptions.
- [x] Add focused service/API tests and backend spec/runbook coverage.
