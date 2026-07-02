# Directory Structure

> Actual backend organization for the stock analysis platform.

---

## Overview

The backend is organized by runtime boundary first, then by feature. FastAPI routes live under `apps/api/routers/`, Celery runtime code lives under `apps/worker/`, reusable business logic lives under `packages/services/`, external data adapters live under `packages/providers/`, SQLAlchemy models live under `packages/domain/`, shared runtime configuration and database setup live under `packages/shared/`, and operational diagnostics live under `scripts/`.

There is currently no `packages/worker/` directory. Worker code in this repository is under `apps/worker/`.

Concrete examples:

- `apps/api/main.py` creates the FastAPI app and includes routers from `apps/api/routers/*.py`.
- `packages/services/market_data.py`, `packages/services/task_runs.py`, and `packages/services/ingestion.py` contain feature logic called by routes and workers.
- `packages/providers/base.py`, `packages/providers/mock_provider.py`, and `packages/providers/yfinance_provider.py` define and implement provider adapters.
- `packages/domain/models.py` is the single SQLAlchemy model module used by services, tests, and Alembic metadata.
- `apps/worker/celery_app.py`, `apps/worker/tasks/ingestion.py`, and `apps/worker/tasks/reports.py` define Celery app configuration and tasks.
- `scripts/provider_readiness.py`, `scripts/dev_health_check.py`, and `scripts/task_run_health.py` are standalone diagnostic entry points.
- `tests/api/`, `tests/services/`, `tests/scripts/`, and `tests/worker/` mirror the backend runtime boundaries.

---

## Directory Layout

```text
apps/
├── api/
│   ├── main.py
│   └── routers/
│       ├── health.py
│       ├── ingestion.py
│       ├── market_data.py
│       └── task_runs.py
└── worker/
    ├── celery_app.py
    └── tasks/
        ├── alerts.py
        ├── ingestion.py
        └── reports.py

packages/
├── domain/
│   └── models.py
├── providers/
│   ├── base.py
│   ├── mock_provider.py
│   ├── yfinance_provider.py
│   ├── akshare_provider.py
│   └── tushare_provider.py
├── services/
│   ├── ingestion.py
│   ├── market_data.py
│   ├── task_dispatch.py
│   └── task_runs.py
└── shared/
    ├── config.py
    ├── database.py
    └── dates.py

alembic/
├── env.py
└── versions/
    ├── 0001_core_schema.py
    └── 0008_alert_triggers_report_task_run.py

scripts/
├── dev_health_check.py
├── provider_readiness.py
├── task_run_health.py
└── verify_celery.py

tests/
├── api/
├── services/
├── scripts/
├── worker/
└── helpers/
```

---

## Layer Responsibilities

### FastAPI app and routers

Routers are intentionally thin. They declare URL prefixes, tags, query parameters, dependency-injected SQLAlchemy sessions, and HTTP error mapping when needed. They delegate actual work to `packages/services/`.

Examples:

- `apps/api/main.py` imports and includes each router explicitly.
- `apps/api/routers/fundamentals.py` accepts `symbol`, `as_of`, and `session`, then calls `get_fundamental_payload()`.
- `apps/api/routers/ingestion.py` builds a task-run input payload and delegates to `enqueue_task_run()`.
- `apps/api/routers/market_data.py` is the router that currently wraps provider/service errors into HTTP responses.

### Services

Services own business behavior, persistence decisions, serialization, fallback behavior, and task-run lifecycle updates. Services usually accept a `Session` when they need database access; read endpoints may accept `Session | None` and fall back to mock/provider data.

Examples:

- `packages/services/market_data.py` resolves providers, reads database bars first when a session is available, and falls back to provider data.
- `packages/services/ingestion.py` writes markets, instruments, and bars and returns quality diagnostics.
- `packages/services/task_runs.py` starts, finishes, fails, retries, and expires `TaskRun` rows.
- `packages/services/task_dispatch.py` maps task names to Celery task dispatchers.

### Providers

Providers are adapters around external market-data sources. The shared contract is `ProviderAdapter` in `packages/providers/base.py`, returning `ProviderInstrument` and `ProviderBar` dataclasses. Provider-specific symbol mapping and normalization stay inside `packages/providers/`.

Examples:

- `packages/providers/base.py` defines the protocol and dataclasses used by services.
- `packages/providers/yfinance_provider.py` maps stock symbols to yfinance tickers and normalizes downloaded dataframes.
- `packages/providers/tushare_provider.py` and `packages/providers/akshare_provider.py` are provider-specific implementations behind the same service boundary.

### Domain models and shared infrastructure

SQLAlchemy ORM models are centralized in `packages/domain/models.py`. Shared runtime configuration and database wiring are centralized in `packages/shared/`.

Examples:

- `packages/domain/models.py` defines tables such as `Market`, `Instrument`, `DailyBar`, `GeneratedReport`, `AlertTrigger`, and `TaskRun`.
- `packages/shared/database.py` defines `Base`, `engine`, `SessionLocal`, and `get_session()`.
- `packages/shared/config.py` defines `Settings` and reads `.env` through pydantic settings.

### Worker runtime

Celery app configuration and periodic schedules live in `apps/worker/celery_app.py`. Task bodies live under `apps/worker/tasks/` and call service-layer functions with a `SessionLocal()` session.

Examples:

- `apps/worker/celery_app.py` configures Redis broker/backend and beat schedules.
- `apps/worker/tasks/ingestion.py` runs market-data ingestion and records `TaskRun` success/failure.
- `apps/worker/tasks/reports.py` refreshes daily stock/watchlist reports and records `TaskRun` results.
- `apps/worker/tasks/alerts.py` evaluates watchlist alerts and records trigger counts.

### Scripts and diagnostics

Scripts are standalone, import the project root when needed, print human-readable status, and avoid writing data unless the script is explicitly an acceptance/runtime action.

Examples:

- `scripts/provider_readiness.py` smoke-checks providers and performs no database writes.
- `scripts/task_run_health.py` checks `TaskRun` reliability state without mutating rows.
- `scripts/dev_health_check.py` checks frontend, API, Redis, and Celery readiness and prints suggested fixes.
- `scripts/verify_celery.py` validates Celery imports, Redis connectivity, and task registration.

### Tests

Tests are grouped by the layer they exercise, not by a single monolithic test directory.

Examples:

- `tests/api/test_ingestion_api.py` uses `TestClient`, dependency overrides, and synchronous Celery helpers.
- `tests/services/test_report_service.py` and `tests/services/test_watchlists_service.py` exercise service behavior against in-memory SQLite.
- `tests/scripts/test_provider_readiness.py` and `tests/scripts/test_task_run_health.py` assert script status semantics.
- `tests/worker/test_tasks.py` and `tests/worker/test_celery_schedule.py` cover worker task behavior and beat schedule configuration.

---

## Naming Conventions

- API router files use feature nouns: `market_data.py`, `task_runs.py`, `watchlists.py`.
- Service files mirror the feature or domain process: `market_data.py`, `ingestion.py`, `task_runs.py`, `watchlist_alerts.py`.
- Provider files end with `_provider.py` when they implement a data provider: `mock_provider.py`, `yfinance_provider.py`, `tushare_provider.py`.
- Celery task names are dotted runtime names such as `ingestion.ingest_market_data`, `reports.refresh_daily_stock_analysis`, and `alerts.evaluate_watchlist_alerts`.
- Test files use `test_<feature>.py` under the relevant layer directory, for example `tests/api/test_market_data_api.py`, `tests/services/test_market_data_service.py`, and `tests/worker/test_tasks.py`.

---

## Common Structure Mistakes

- Do not put business rules directly into a router when a nearby service already owns that feature. Follow `apps/api/routers/ingestion.py` delegating to `packages/services/task_runs.py`.
- Do not bypass provider adapters from routers or workers. Follow `packages/services/market_data.py` calling `get_provider()` and provider methods behind `ProviderAdapter`.
- Do not add worker code under `packages/worker/`; the current worker runtime is `apps/worker/`.
- Do not duplicate SQLAlchemy models in feature packages. `packages/domain/models.py` is the current model source of truth.
