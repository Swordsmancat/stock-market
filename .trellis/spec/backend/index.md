# Backend Development Guidelines

> Current backend conventions for the stock analysis platform.

---

## Overview

The backend is a Python service stack built around FastAPI routers, SQLAlchemy ORM models and sessions, provider adapters for market data, service-layer business logic, Celery worker tasks, diagnostic scripts, and focused pytest coverage. These guidelines document patterns already present in the repository; they are not a wishlist for a future architecture.

Primary examples:

- `apps/api/main.py` wires the FastAPI app and routers.
- `apps/api/routers/task_runs.py`, `apps/api/routers/fundamentals.py`, and `apps/api/routers/ingestion.py` show router-to-service wiring.
- `packages/services/market_data.py`, `packages/services/task_runs.py`, and `packages/services/news.py` hold backend business logic.
- `packages/providers/yfinance_provider.py`, `packages/providers/tushare_provider.py`, and `packages/providers/base.py` define external data boundaries.
- `packages/domain/models.py` contains SQLAlchemy domain models.
- `packages/shared/database.py` owns the SQLAlchemy engine, `SessionLocal`, and FastAPI session dependency.
- `apps/worker/tasks.py`, `apps/worker/tasks/`, and `apps/worker/celery_app.py` contain worker execution and schedule wiring.
- `scripts/provider_readiness.py`, `scripts/dev_health_check.py`, and `scripts/task_run_health.py` are lightweight diagnostics.
- `tests/api/`, `tests/services/`, `tests/scripts/`, and `tests/worker/` provide focused regression coverage.

---

## Pre-Development Checklist

- Identify the layer being changed: API router, service, provider, domain model, shared config/database, worker, script, or test.
- Read the matching guideline file below before editing backend code.
- Prefer adding behavior at the same layer used by nearby examples instead of bypassing routers, services, or providers.
- Do not commit or push from backend subagent work unless the user explicitly asks for it.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Actual FastAPI, service, provider, domain, worker, script, and test layout | Filled |
| [Database Guidelines](./database-guidelines.md) | SQLAlchemy sessions, ORM models, migrations, and SQLite test fixtures | Filled |
| [Error Handling](./error-handling.md) | HTTPException mapping, provider boundary errors, and diagnostic WARN/FAIL semantics | Filled |
| [Quality Guidelines](./quality-guidelines.md) | Focused pytest, non-mutating diagnostics, and subagent safety boundaries | Filled |
| [Logging Guidelines](./logging-guidelines.md) | Current logging state and sensitive-data boundaries | Filled |
| [Assistant Research Citation Contract](./assistant-research-citation-contract.md) | OpenAI-compatible configuration, one-click secret-safe connection testing, `/assistant/market` citations, diagnostics, and safety boundaries | Filled |
| [Instrument List Query Contract](./instrument-list-query-contract.md) | Additive bounded instrument filtering/pagination with legacy complete-list compatibility | Filled |
| [News Search Provider Contract](./news-search-provider-contract.md) | Configurable search provider settings, adapter diagnostics, storage/citation boundary, and no-secret payload rules | Filled |
| [InStock-Inspired Analysis Pattern Contract](./instock-analysis-pattern-contract.md) | Stored InStock-inspired technical indicators, candlestick patterns, chip distribution, attribution boundary, and no-trading rules | Filled |
| [InStock-Inspired Composite Stock Selection Contract](./instock-composite-stock-selection-contract.md) | Research-only local composite stock selection over stored technical/fundamental evidence | Filled |
| [InStock-Inspired Data Job Contract](./instock-data-job-contract.md) | Single-symbol daily stock/ETF ingestion job signatures, diagnostics, and no-trading boundary | Filled |
| [Market Daily Data Contract](./market-daily-data-contract.md) | Provider-backed A-share stock fund-flow, industry/concept flow, and limit-up context with no-citation/no-trading boundary | Filled |
| [Stored Market Movers Contract](./market-movers-contract.md) | Read-only exact-date A-share gainers/losers over one coherent stored daily-bar cohort | Filled |
| [Stored Stock Comparison Contract](./market-comparison-contract.md) | Read-only A-share overlay comparison over coherent cohorts and exact shared dates | Filled |
| [Market Daily Evidence Contract](./market-daily-evidence-contract.md) | Persisted provider-normalized daily market evidence, deterministic citations, dedupe, diagnostics, and Evidence Center refresh | Filled |
| [Recommendation Signal Evaluation Contract](./recommendation-signal-evaluation-contract.md) | Public historical signal evaluation API, metrics payload, diagnostics, and no-trading boundary | Filled |
| [InStock-Inspired Strategy Screening Contract](./instock-strategy-screening-contract.md) | Research-only strategy screening/evaluation API, InStock attribution boundary, and no-trading rules | Filled |
| [Market Indicator Seed Import Contract](./market-indicator-seed-import-contract.md) | Offline audited JSON/CSV macro observation import contract, validation rules, and CLI boundary | Filled |
| [Official Macro Refresh Contract](./official-macro-refresh-contract.md) | Explicit database-first macro provider refresh, audited observations, and FR007/FDR007 semantics | Filled |
| [Economic Calendar Contract](./economic-calendar-contract.md) | Explicit public economic calendar refresh, stable stored events, database-only reads, and localized display | Filled |
| [Hot Sector Contract](./hot-sector-contract.md) | `/sectors/hot` provider-backed payload fields, degraded states, and cross-layer tests | Filled |
| [Eastmoney Industry Ranking History Contract](./eastmoney-industry-ranking-history-contract.md) | Stored direct-first/proxy-fallback Eastmoney industry ranking history and secret-safe access | Filled |
| [Intraday Minute Cache Contract](./intraday-cache-contract.md) | `/market-data/{symbol}/intraday` verified minute cache, session policy, freshness metadata, and no-fabrication rules | Filled |
| [Market Depth Contract](./market-depth-contract.md) | `/market-data/{symbol}/depth` explicit provider boundary, section-level degraded states, large-order derivation, and no-fabrication rules | Filled |
| [Comprehensive A-share Research Coverage Contract](./a-share-research-coverage-contract.md) | Full A-share universe sync, bulk screening, transparent profiles, validated AI shortlist explanation, and corporate-action evidence batches | Filled |
| [Persisted Daily Research Shortlist Contract](./daily-research-shortlist-contract.md) | Immutable point-in-time daily cohort, transparent scoring, concurrency/idempotency, localized display, and frozen evidence provenance | Filled |
| [Personal Research Identity, Financial State, and Daily-Bar Fallback Contract](./personal-research-workflow-contract.md) | Exact instrument/watchlist identity, trustworthy financial states, and market-aware database-first CN daily-bar fallback through detail and AI | Filled |
| [Local Compose Runtime Contract](./local-compose-runtime-contract.md) | Default Docker Desktop full-stack services, ports, health ordering, restart behavior, and isolated acceptance compatibility | Filled |
| [Read-Only Database Storage Overview Contract](./storage-overview-contract.md) | Secret-safe PostgreSQL catalog statistics, stable data-domain grouping, SQLite test compatibility, and desktop storage UI ownership | Filled |
| [Eastmoney Public Fundamentals Fallback Contract](./eastmoney-public-fundamentals-contract.md) | Database-first, Cookie-free A-share fundamentals/company fallback, normalized cache, detail, and assistant citation boundaries | Filled |
| [Research Shortlist Outcome Contract](./research-shortlist-outcome-contract.md) | Frozen 5/20/60-session outcomes for published cohorts, completed-bar evidence, bounded candidate windows, and exact CSI 300 comparison | Filled |
| [Daily Research Loop Automation Contract](./daily-research-loop-contract.md) | Trusted completed-market watermark, bounded due-cohort maturation, immutable publication, and TaskRun/Beat lifecycle | Filled |
| [Official Disclosure Metadata Contract](./official-disclosure-metadata-contract.md) | CNINFO metadata refresh, stable document identity, metadata-only citations, and no-body-inference boundary | Filled |
| [Official Disclosure Document Contract](./official-disclosure-document-contract.md) | Exact CNINFO PDF discovery, content-addressed versions, bounded extraction, page citations, and no-OCR boundary | Filled |
| [Official Disclosure Operations Contract](./official-disclosure-operations-contract.md) | Watchlist coverage, durable incremental cursors, freshness/SLA, bounded sequential CNINFO batches, and TaskRun/Beat operations | Filled |

---

## Quality Check

- Specs should point to real files instead of generic best practices.
- New backend guidance should include multiple repository path examples.
- Lightweight validation can use `python ./.trellis/scripts/task.py validate 00-bootstrap-guidelines`; if another layer is still unfilled, record that validation failure instead of editing out-of-scope specs.

---

**Language**: All documentation should be written in **English**.
