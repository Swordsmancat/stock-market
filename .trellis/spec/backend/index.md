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
| [Assistant Research Citation Contract](./assistant-research-citation-contract.md) | `/assistant/market` research-evidence citations, diagnostics, LLM citation validation, and safety boundaries | Filled |
| [News Search Provider Contract](./news-search-provider-contract.md) | Configurable search provider settings, adapter diagnostics, storage/citation boundary, and no-secret payload rules | Filled |
| [InStock-Inspired Analysis Pattern Contract](./instock-analysis-pattern-contract.md) | Stored candlestick-pattern research signals, InStock attribution boundary, and no-trading rules | Filled |
| [Recommendation Signal Evaluation Contract](./recommendation-signal-evaluation-contract.md) | Public historical signal evaluation API, metrics payload, diagnostics, and no-trading boundary | Filled |
| [InStock-Inspired Strategy Screening Contract](./instock-strategy-screening-contract.md) | Research-only strategy screening/evaluation API, InStock attribution boundary, and no-trading rules | Filled |
| [Market Indicator Seed Import Contract](./market-indicator-seed-import-contract.md) | Offline audited JSON/CSV macro observation import contract, validation rules, and CLI boundary | Filled |
| [Hot Sector Contract](./hot-sector-contract.md) | `/sectors/hot` provider-backed payload fields, degraded states, and cross-layer tests | Filled |
| [Intraday Minute Cache Contract](./intraday-cache-contract.md) | `/market-data/{symbol}/intraday` verified minute cache, session policy, freshness metadata, and no-fabrication rules | Filled |
| [Market Depth Contract](./market-depth-contract.md) | `/market-data/{symbol}/depth` explicit provider boundary, section-level degraded states, large-order derivation, and no-fabrication rules | Filled |

---

## Quality Check

- Specs should point to real files instead of generic best practices.
- New backend guidance should include multiple repository path examples.
- Lightweight validation can use `python ./.trellis/scripts/task.py validate 00-bootstrap-guidelines`; if another layer is still unfilled, record that validation failure instead of editing out-of-scope specs.

---

**Language**: All documentation should be written in **English**.
