# Complete market data acquisition and display workflow - Design

## Summary

The current application has many pieces of a stock analysis platform, but the product workflow is incomplete. Backend providers, ingestion, reports, task runs, and frontend pages exist, yet users cannot reliably answer these questions:

- Which provider is currently active?
- Is the displayed price real provider data, mock data, or database data from an earlier task?
- Can I fetch data for this specific symbol, or only for the provider's fixture universe?
- Where do I browse all instruments and inspect market data freshness?
- What task was created when I clicked ingestion or analysis refresh, and did it produce usable bars/reports?

This design defines an incremental daily-bars workflow. It does not promise true real-time quote support in the first slice. Instead, it makes the existing historical/latest daily bar system honest, visible, and usable.

## Current-state audit

### Backend providers

Relevant files:

- `packages/providers/base.py`
- `packages/providers/mock_provider.py`
- `packages/providers/yfinance_provider.py`
- `packages/providers/akshare_provider.py`
- `packages/providers/tushare_provider.py`
- `packages/services/platform_settings.py`
- `packages/services/market_data.py`
- `apps/api/routers/market_data.py`

Current state:

- `ProviderAdapter` supports `fetch_instruments()` and `fetch_bars()`. It does not define a real-time quote contract.
- `mock` is deterministic fixture data only.
- `yfinance` can provide real historical daily bars, but it is not a true real-time quote source.
- `akshare` and `tushare` are intended for China market historical data, but they depend on optional dependencies and/or token configuration.
- Provider instrument universes are fixture-like, so market-wide ingestion does not cover arbitrary user-entered symbols.
- Several API routers default `provider` to `mock`, which can bypass platform settings and confuse users who configured a different provider.

### Market-data and ingestion flow

Relevant files:

- `apps/api/routers/market_data.py`
- `apps/api/routers/ingestion.py`
- `apps/api/routers/analysis.py`
- `apps/api/routers/reports.py`
- `packages/services/ingestion.py`
- `packages/services/market_data.py`
- `packages/services/analysis.py`
- `packages/services/reports.py`
- `apps/worker/tasks/ingestion.py`
- `apps/worker/tasks/reports.py`

Current state:

1. `GET /market-data/{symbol}/bars` reads database daily bars first when a session is present, then falls back to provider bars.
2. `GET /market-data/{symbol}/latest` returns the latest database daily bar or the last provider daily bar from a short date window. This is a latest daily bar, not a real-time quote.
3. `POST /ingestion/snapshot` enqueues `ingestion.ingest_market_data`; the API does not synchronously write bars.
4. Worker ingestion writes `Market`, `Instrument`, and `DailyBar` records and records `quality_diagnostics` in task results.
5. `refresh_stock_analysis()` orchestrates ingestion, indicators, news, fundamentals, and report generation.
6. `generate_stock_report_payload()` assumes at least one bar exists; empty provider results can become opaque errors.

### Frontend display flow

Relevant files:

- `apps/web/app/[locale]/page.tsx`
- `apps/web/app/[locale]/instruments/[symbol]/page.tsx`
- `apps/web/app/[locale]/reports/page.tsx`
- `apps/web/app/[locale]/reports/[reportId]/page.tsx`
- `apps/web/app/[locale]/task-runs/page.tsx`
- `apps/web/app/[locale]/task-runs/[taskRunId]/page.tsx`
- `apps/web/app/[locale]/settings/page.tsx`
- `apps/web/components/price-chart.tsx`
- `apps/web/components/ingestion-trigger-form.tsx`
- `apps/web/components/analysis-trigger-form.tsx`
- `apps/web/components/generate-daily-report-button.tsx`

Current state:

- Dashboard displays a primary instrument and related cards, but it is not a market-data browser.
- Instrument detail displays charts, reports, indicators, fundamentals, and news, but source/provider/freshness are not prominent enough.
- Reports and Task Runs are now better linked, but user-triggered ingestion/analysis actions still do not consistently surface task-run links.
- Settings lets users save provider configuration, but it does not show provider readiness or test connection status.
- There is no `apps/web/app/[locale]/instruments/page.tsx` list page and no dedicated market-data page.

## Product semantics

### Daily historical bars

Daily bars are OHLCV records for a trading day. They can come from:

- database rows previously ingested;
- a provider fallback in `get_bars_payload()`;
- mock fixtures during development/tests.

The UI should label these as daily bars, not real-time data.

### Latest daily bar

The current `latest` endpoints should be treated as latest daily bar endpoints. They should expose or display:

- `symbol`;
- `timestamp` / `as_of`;
- `close`;
- `source`;
- effective/requested provider where available;
- whether data came from database or provider fallback.

### Real-time quote

True quote support is future work. It needs a separate provider contract such as `ProviderQuote` / `fetch_latest_quote()` and endpoint semantics such as `/market-data/{symbol}/quote`. Until then, UI copy should avoid implying real-time data.

## Target daily-bars workflow

```text
User selects provider/symbol/market/date range
  -> frontend submits ingestion or analysis action
  -> API enqueues TaskRun with requested provider and symbol/market/date input
  -> worker fetches provider daily bars
  -> service writes DailyBar rows and quality diagnostics
  -> TaskRun result records provider/source/bar_count/no_data reason
  -> frontend links user to TaskRun detail
  -> market-data/instrument page displays latest daily bar, history, source, freshness, and task/report links
```

## Proposed child tasks

### Child 1: Provider settings and readiness visibility

Goal:

- Make provider configuration understandable and effective.
- Avoid exposing secrets.
- Add readiness/capability information before users trigger data fetches.

Likely files:

- `packages/services/platform_settings.py`
- `packages/services/market_data.py`
- `scripts/provider_readiness.py`
- `apps/api/routers/settings.py`
- `apps/web/app/[locale]/settings/page.tsx`
- `apps/web/messages/en.json`
- `apps/web/messages/zh.json`

Key decisions:

- Provider query defaults should not unintentionally force `mock` when platform settings choose another provider.
- `tushare_token` should be masked in public settings payloads.
- Readiness should be non-mutating and should not require real network in default tests.

### Child 2: Single-symbol daily-bar ingestion workflow

Goal:

- Let users fetch daily bars for a specific symbol/market/provider/date range without relying on provider fixture instruments.

Likely files:

- `apps/api/routers/ingestion.py`
- `apps/worker/tasks/ingestion.py`
- `packages/services/ingestion.py`
- `packages/services/task_dispatch.py`
- `tests/api/test_ingestion_api.py`
- `tests/services/test_ingestion_service.py`
- `tests/worker/test_tasks.py`

Key decisions:

- Keep the existing market snapshot path for batch ingestion.
- Add a symbol-targeted path instead of overloading fixture market ingestion.
- Preserve idempotent upsert behavior for `DailyBar`.

### Child 3: No-data and provider error UX contract

Goal:

- Prevent empty provider results from becoming opaque 500 errors.
- Return and display actionable reasons for missing data.

Likely files:

- `packages/services/market_data.py`
- `packages/services/reports.py`
- `packages/services/analysis.py`
- `apps/api/routers/market_data.py`
- `apps/api/routers/reports.py`
- `apps/api/routers/analysis.py`
- `apps/web/app/[locale]/instruments/[symbol]/page.tsx`
- `apps/web/messages/en.json`
- `apps/web/messages/zh.json`

Key decisions:

- Distinguish invalid input, provider unavailable, provider empty/no-data, and task dispatch failure.
- Keep provider exception messages sanitized.

### Child 4: Instruments / market-data display page

Goal:

- Add a clear UI entry point for browsing instruments and inspecting latest daily-bar state.

Likely files:

- `apps/web/app/[locale]/instruments/page.tsx`
- `apps/web/app/[locale]/instruments/page.test.tsx`
- `apps/web/components/sidebar-navigation.tsx`
- `apps/web/components/mobile-navigation.tsx`
- `apps/web/messages/en.json`
- `apps/web/messages/zh.json`

Initial page fields:

- symbol;
- name;
- market;
- latest close;
- latest timestamp/as-of;
- source/provider;
- freshness badge;
- links to detail/report/task actions.

### Child 5: Instrument detail source/freshness and OHLCV table

Goal:

- Turn the instrument detail page into a usable single-symbol data workstation.

Likely files:

- `apps/web/app/[locale]/instruments/[symbol]/page.tsx`
- `apps/web/app/[locale]/instruments/[symbol]/page.test.tsx`
- `apps/web/components/price-chart.tsx`
- `apps/web/messages/en.json`
- `apps/web/messages/zh.json`

Key decisions:

- Chart copy and empty states should be localized.
- Add daily bars count and last timestamp.
- Add a compact OHLCV table for recent bars.

### Child 6: Task-run feedback from user actions

Goal:

- When a user triggers ingestion/analysis/report generation, show the related task-run/report link.

Likely files:

- `apps/web/app/[locale]/actions.ts`
- `apps/web/components/ingestion-trigger-form.tsx`
- `apps/web/components/analysis-trigger-form.tsx`
- `apps/web/components/generate-daily-report-button.tsx`
- `apps/web/lib/task-run-poll.ts`
- `apps/web/messages/en.json`
- `apps/web/messages/zh.json`

Key decisions:

- Prefer links to task-run detail for asynchronous operations.
- Keep polling optional and contained to client components.

## Out of scope for the parent first wave

- WebSocket or streaming quotes.
- Full market universe discovery.
- Row-level `DailyBar` provider lineage schema migration unless a child task proves it is required.
- CI tests that hit real provider networks.
- Portfolio or alert product redesign beyond links to instrument/market-data pages.

## Validation strategy

Backend focused tests:

```powershell
python -m pytest tests/api/test_market_data_api.py tests/services/test_market_data_service.py -v
python -m pytest tests/api/test_ingestion_api.py tests/services/test_ingestion_service.py tests/worker/test_tasks.py -v
python -m pytest tests/api/test_reports_api.py tests/services/test_report_service.py tests/api/test_analysis_api.py -v
python -m pytest tests/scripts/test_provider_readiness.py tests/scripts/test_task_run_health.py -v
```

Frontend focused tests:

```powershell
npm run test:web -- "apps/web/app/[locale]/instruments/page.test.tsx"
npm run test:web -- "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx" "apps/web/app/[locale]/page.test.tsx"
npm run test:web -- "apps/web/app/[locale]/actions.test.ts" "apps/web/components/generate-daily-report-button.test.tsx"
```

Broad confidence checks:

```powershell
python -m pytest
npm run test:web
```
