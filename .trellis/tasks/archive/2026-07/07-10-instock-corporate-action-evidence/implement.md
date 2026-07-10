# InStock Comprehensive A-share Research Coverage Implementation Plan

## 1. Planning and Safety Gate

- [x] Run the PRD convergence pass and verify no blocking open decisions remain.
- [x] Validate the task artifacts before activation.
- [x] Start the task only after the user approves this final plan.
- [x] Before code edits, load `trellis-before-dev` and all relevant backend,
  frontend, database, citation, and cross-layer specifications.
- [x] Preserve the unrelated `07-03-professional-financial-dashboard` task.

## 2. Universe Provider Contract

- [x] Add normalized universe snapshot/result types and an additive
  `InstrumentUniverseProvider` protocol in `packages/providers/base.py`.
- [x] Add an injected AkShare A-share universe downloader/parser using
  `stock_info_a_code_name()` without changing the existing market-snapshot
  `fetch_instruments()` behavior.
- [x] Normalize Shanghai/Shenzhen/Beijing symbols and emit degraded diagnostics
  for malformed codes or unknown exchange prefixes.
- [x] Add provider unit tests for success, duplicate rows, malformed rows,
  empty output, and downloader failure without live network access.

## 3. Persistence and Migration

- [x] Add nullable `Instrument.universe_provider` and
  `Instrument.universe_synced_at` fields.
- [x] Add `InstrumentUniverseSync` model with source/freshness/reconciliation
  counts and JSON diagnostics.
- [x] Add Alembic revision `0014` with PostgreSQL/SQLite-compatible upgrade and
  downgrade operations.
- [x] Extend migration tests and `Base.metadata.create_all()` expectations.

## 4. Universe Sync Service

- [x] Add `packages/services/instrument_universe.py` with normalization,
  reconciliation, serialization, latest-status, and failure-safe behavior.
- [x] Upsert market/exchange/instrument rows and reactivate seen rows.
- [x] Deactivate only rows managed by the same provider after a valid complete
  snapshot; never deactivate on empty/provider/schema/storage failure.
- [x] Return inserted/updated/unchanged/reactivated/deactivated/skipped counts
  and sanitized diagnostics.
- [x] Add SQLite service tests for repeat sync, rename/update, reactivation,
  safe deactivation, manual-row preservation, empty/provider failure, and
  transaction rollback.

## 5. TaskRun, Dispatch, Worker, and API

- [x] Add `update_task_run_progress(...)` while preserving existing TaskRun
  serialization and final-result behavior.
- [x] Add `ingestion.sync_instrument_universe` dispatch mapping and worker task.
- [x] Add `POST /ingestion/instrument-universe` with normalized TaskRun input.
- [x] Add `GET /stock-selection/universe-status` backed by local sync history.
- [x] Extend synchronous Celery test helper, API, dispatch, worker, retry, and
  task-run tests.

## 6. Scalable Full-Universe Selection

- [x] Remove the pre-evaluation 100-candidate cap while retaining returned-item
  limit bounds.
- [x] Add bulk evidence loaders for latest bars, indicators, fundamentals, and
  conditional news/sentiment data.
- [x] Refactor criterion evaluation to consume evidence bundles without
  per-instrument database queries.
- [x] Add aggregate coverage counters and compact missing-source diagnostics.
- [x] Preserve explicit-symbol, market, asset-type, watchlist-only, citation,
  safety, and invalid-request behavior.
- [x] Add a regression with more than 100 instruments proving a matching symbol
  after position 100 is evaluated and can rank into results.

## 7. Named Profiles

- [x] Define `balanced_research`, `quality_value`, and `trend_liquidity` in one
  backend profile registry.
- [x] Expose `GET /stock-selection/profiles` with labels/descriptions, visible
  default criteria, supported overrides, and safety metadata.
- [x] Add profile resolution to discovery while leaving explicit `/screen`
  criteria backward compatible.
- [x] Test unknown profile, invalid override, effective-criteria echo, and
  deterministic ranking.

## 8. AI Shortlist Explanation

- [x] Add a dedicated AI prompt/fallback module for shortlist comparison.
- [x] Add a service that runs deterministic selection, bounds the shortlist,
  assembles stored citations, and optionally calls the configured LLM.
- [x] Validate generated inline citations and mentioned candidate symbols;
  unknown values trigger deterministic fallback diagnostics.
- [x] Add `POST /stock-selection/discover` request/response models and route.
- [x] Add tests for deterministic fallback, fake LLM success, provider failure,
  empty shortlist, unknown citation, unknown symbol, and no-trading wording.

## 9. Corporate-Action Enrichment

- [x] Add provider-normalized dividend/bonus-transfer and rights-allotment
  payloads with injected downloaders and fake DataFrame tests.
- [x] Add deterministic report-period/symbol-batch job input, cursor, partial
  success, TaskRun progress, and retry diagnostics.
- [x] Extend market-daily evidence event registry, loader, identity, excerpt,
  filtering, and citation assembly for `dividend_bonus` and
  `rights_allotment`.
- [x] Preserve multiple distinct events for one symbol/date with a normalized
  fingerprint and keep mock/error/empty rows non-citable.
- [x] Add service/API/worker/evidence/assistant/dashboard/research-brief tests.

## 10. Frontend Integration

- [x] Add Next proxies for universe sync/status, profiles, and discovery.
- [x] Extend AI Research with universe freshness/coverage, refresh TaskRun link,
  profile selector, visible criteria, discovery states, shortlist table, AI
  explanation, citations, diagnostics, and existing assistant handoff.
- [x] Extend Evidence Center labels/counts/diagnostics for corporate actions.
- [x] Keep mutations client-side through proxies and refresh server data after
  completion; do not add a global state store.
- [x] Update English and Chinese catalogs together and verify UTF-8/ICU-safe
  messages.
- [x] Add route, component, page, loading, empty, failure, and legacy-payload
  tests.

## 11. Documentation and Contracts

- [x] Add an A-share universe/coverage backend contract and index entry.
- [x] Update composite-selection, data-job, market-daily-evidence, assistant
  citation, and InStock runbook contracts.
- [x] Update README and user/developer documentation with explicit completeness,
  refresh, provider, safety, and no-trading boundaries.

## 12. Validation

- [x] Run focused provider/universe/service/migration tests.
- [x] Run focused TaskRun/dispatch/worker/API tests.
- [x] Run focused selection/profile/discovery/AI validation tests.
- [x] Run focused corporate-action/evidence/citation tests.
- [x] Run focused frontend route/component/page tests.
- [x] Run ruff on all touched Python files.
- [x] Run TypeScript no-emit check and locale JSON parsing.
- [x] Run the full Python test suite.
- [x] Run the full Web test suite.
- [x] Run Trellis task validation and `git diff --check`.
- [x] Record validation results in this file before commit planning.

### Validation Results — 2026-07-10

- Focused backend provider/universe/migration, TaskRun/dispatch/worker/API,
  selection/profile/discovery, and corporate-action/evidence suites passed.
- Touched-file Ruff check passed. A repository-wide Ruff scan additionally
  reported three pre-existing unused imports in unrelated files
  (`packages/services/news.py`, `tests/ai/test_llm_report.py`, and
  `tests/services/test_fundamentals_yfinance.py`); this task did not modify them.
- TypeScript `--noEmit` passed.
- English and Chinese locale JSON parsing passed.
- Full Python suite: `527 passed`.
- Full Web suite: `64 files passed`, `194 tests passed`.
- Trellis task validation passed for both zero-entry inline-mode JSONL files.
- `git diff --check` passed; Git emitted only repository line-ending warnings.

## Risk and Rollback Points

- Universe fetch and reconciliation: do not commit/deactivate until the full
  normalized snapshot is known valid.
- Existing market ingestion: never route the full universe through the old
  snapshot-plus-bars `fetch_instruments()` path.
- Selection performance: keep the old evaluator behavior covered while moving
  data access to bulk loaders; roll back the loader refactor if query count or
  result parity regresses.
- AI: deterministic shortlist and fallback remain authoritative even when LLM
  generation is disabled or rejected.
- Corporate actions: event types are additive and reuse the evidence table;
  disabling their job must not affect existing five event types.
- Frontend: new AI Research panels are additive and must preserve current
  watchlist/followed/manual-symbol workflows.
