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

## Social Sentiment Evidence Boundary Slice

- [x] Add candidate-level `evidence_boundary` payloads for live news/search candidates.
- [x] Classify `social` and `public_opinion` result kinds as low-strength social signals.
- [x] Defer social/public-opinion candidates from `NewsArticle` and `SentimentSignal` persistence during `search-ingest`.
- [x] Return `social_candidate_count` and `social_candidates_deferred` from `search-ingest`.
- [x] Add source-readiness guidance for future social sentiment storage as non-citable today.
- [x] Add focused service/source-readiness tests and backend spec/runbook coverage.

## InStock Chip Distribution Slice

- [x] Confirm InStock CYQ/chip distribution is a capability reference, not a runtime import target.
- [x] Add pure Python/pandas latest-window chip distribution over local OHLCV bars.
- [x] Persist `chip_distribution` through the existing `TechnicalIndicator` table.
- [x] Mark the payload as a volume-normalized approximation because free-float/turnover inputs are not stored.
- [x] Preserve existing numeric indicators, K-line pattern outputs, and stored technical-indicator citation boundary.
- [x] Add focused analytics, service, and API tests.
- [x] Add runbook/spec coverage for Apache-2.0 attribution, approximation limits, and no-trading rules.

## InStock Expanded Technical Indicators Slice

- [x] Add pure Python/pandas formulas for `cci`, `obv`, `roc`, `bias`, `mfi`, and `william_r`.
- [x] Persist the expanded daily indicator set through the existing `TechnicalIndicator` table.
- [x] Preserve existing numeric indicator, candlestick-pattern, and chip-distribution payload shapes.
- [x] Keep all indicator values research-only and out of trading/order-intent boundaries.
- [x] Add focused analytics, service, and API tests.
- [x] Add runbook/spec coverage for no-TA-Lib/no-runtime-import/no-trading rules.

## InStock Composite Stock Selection Slice

- [x] Add a local evidence screener over stored instruments, daily bars, technical indicators, and fundamentals.
- [x] Support first composite criteria: max PE, revenue growth, net margin, RSI range, and close above MA.
- [x] Add `GET /stock-selection/screen` as a thin route over the service boundary.
- [x] Return matched rule details, diagnostics, stored evidence citations, `research_signal_only=true`, and a non-advice disclaimer.
- [x] Avoid live provider scans, persistence of selection results, InStock runtime imports, order intents, and buy/sell advice.
- [x] Add focused service/API tests and backend spec/runbook coverage.

## InStock Composite Stock Selection Technical Evidence Criteria Slice

- [x] Extend `screen_local_stock_selection` with stored technical-evidence criteria for candlestick pattern codes, MFI, William %R, and chip-distribution benefit ratio.
- [x] Add `GET /stock-selection/screen` query parameters for `required_pattern_codes`, MFI range, William %R range, and chip benefit-ratio range.
- [x] Preserve local-only evidence reads from latest stored `TechnicalIndicator` rows and avoid live provider scans.
- [x] Return missing nested indicator payloads as diagnostics, not fabricated neutral values.
- [x] Keep the response research-only with stored evidence citations and the non-advice disclaimer.
- [x] Add focused service/API tests and backend spec/runbook coverage.

## InStock Watchlist-Scoped Composite Stock Selection Slice

- [x] Add a local-only active watchlist scope helper that returns `symbol`/`market` pairs without provider-backed enrichment.
- [x] Add `watchlist_only` to `screen_local_stock_selection` and `GET /stock-selection/screen`.
- [x] Intersect watchlist scope with optional symbols/market filters before criteria evaluation.
- [x] Return `candidate_scope` in stock-selection payloads for auditability.
- [x] Preserve stored evidence citations, `research_signal_only=true`, and the non-advice disclaimer.
- [x] Add focused service/API/watchlist tests and backend spec/runbook coverage.

## InStock Single-Symbol Stock / ETF Daily-Bar Job Slice

- [x] Add `asset_type` to `POST /ingestion/symbol-daily-bars`, defaulting to `stock` and supporting `stock` / `etf`.
- [x] Propagate `asset_type` through TaskRun input, task dispatch, Celery worker kwargs, worker result payload, serialized snapshot, and persisted `Instrument.asset_type`.
- [x] Preserve targeted provider fetches by symbol/timeframe/date range without importing InStock schedulers, ETF crawlers, proxy/cookie workflows, or database runtime.
- [x] Reject unsupported asset types before provider fetch and avoid fabricated rows when providers return no data.
- [x] Add focused service/API/dispatch/worker tests and backend spec/runbook coverage.
