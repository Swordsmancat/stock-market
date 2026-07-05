# Stock Analysis Platform

Internal research platform for multi-market stock analysis: market data ingestion, technical indicators, AI reports, watchlist alerts, and simulated portfolios.

## Quick start

1. Copy environment variables:

```bash
cp .env.example .env
```

2. Start infrastructure (PostgreSQL + Redis + optional API/workers):

```bash
docker compose up -d db redis
# full stack with API:
docker compose up -d db redis api worker beat
```

For A-share data providers:

```bash
pip install -e ".[cn-market]"
```

3. Install Python dependencies and run migrations:

```bash
pip install -e .
alembic upgrade head
```

4. Start backend API (separate terminal):

```bash
uvicorn apps.api.main:app --reload --port 8000
```

If port 8000 is occupied by an old process, use another port and set `API_BASE_URL` in `apps/web/.env.local`:

```bash
uvicorn apps.api.main:app --reload --port 8001
```

5. Start background workers (optional, for async tasks):

```bash
celery -A apps.worker.celery_app.celery_app worker --loglevel=info
celery -A apps.worker.celery_app.celery_app beat --loglevel=info
```

6. Start the web app:

```bash
npm install
npm run dev:web
```

If the frontend does not open, run the local health check before restarting services:

```bash
python scripts/dev_health_check.py
```

The check reports whether port 3000 is listening, whether `/zh` responds, and whether API/Redis/Celery dependencies are reachable.

Open [http://localhost:3000/en](http://localhost:3000/en).

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/manual/user-guide.md](docs/manual/user-guide.md) | User-facing guide for Phase 2 / Phase 3 financial analysis features and current capability status |
| [docs/runbooks/developer-maintenance.md](docs/runbooks/developer-maintenance.md) | Maintainer guide for endpoints, degraded-safe provider contracts, validation, and roadmap gaps |
| [docs/runbooks/local-development.md](docs/runbooks/local-development.md) | Full local setup, env vars, testing |
| [docs/runbooks/mvp-acceptance.md](docs/runbooks/mvp-acceptance.md) | Original MVP acceptance checklist |
| [CONTEXT.md](CONTEXT.md) | Domain terminology |
| [docs/superpowers/plans/2026-07-01-priority-5-6-7.md](docs/superpowers/plans/2026-07-01-priority-5-6-7.md) | Latest implementation plan |
| [docs/superpowers/plans/2026-07-01-implementation-gap-closure.md](docs/superpowers/plans/2026-07-01-implementation-gap-closure.md) | Current implementation status and gap-closure plan |

## Key features

- **Market data**: yfinance provider (US/HK/CN), provider-neutral `/ingestion/snapshot`, Celery scheduled ingestion
- **Analysis pipeline**: indicators, fundamentals, news, AI daily reports, AI market assistant
- **Watchlist alerts**: price/RSI rules with trigger history
- **Portfolios**: multi-portfolio CRUD with demo fallback
- **Task runs**: async ingestion/analysis with retry and report linking
- **Sector rotation**: provider-backed `/sectors/hot` contract with explicit data modes, fund-flow definitions, and degraded-safe fallback states

## Phase 2 / Phase 3 feature status

| Phase | Feature | Status | Notes |
|---|---|---:|---|
| Phase 2 | K-line interaction enhancements | Complete | Interactive candlestick charts include range controls and MA / BOLL / volume / MACD / RSI / KDJ indicator controls. |
| Phase 2 | Smart recommendations | Complete | Breakout, oversold rebound, volume anomaly, and momentum-style research signals are available as research aids. |
| Phase 2 | Hot sector rotation | Partial / provider-backed MVP | `/sectors/hot` now returns a normalized provider contract with sector taxonomy, flow definitions, live/delayed/mock/unavailable data modes, top constituent metadata, breadth, contribution, provider capability, and explicit rotation-history availability. The default static fixture is explicitly `degraded + mock`; verified production fund-flow and persisted rotation history depend on provider availability such as AkShare/Tushare/Eastmoney-style integrations. |
| Phase 2 | Comparison analysis | Complete | Correlation-oriented comparison tooling is available. |
| Phase 3 | Intraday chart | Partial / provider-backed MVP | `GET /market-data/{symbol}/intraday` now supports verified yfinance `1m` minute bars when available, including previous-close references and `ok` / `no_data` / `degraded` payloads. Mock, AkShare, and Tushare remain degraded until explicit minute-bar providers are verified. |
| Phase 3 | Market depth | Partial / provider-boundary MVP | `GET /market-data/{symbol}/depth` now uses an explicit `fetch_market_depth` provider boundary, section-level `ok` / `degraded` semantics, verified order-book / recent-trade / fund-flow normalization, and large-order derivation only from verified trades. AkShare now has a fixture-tested order-book candidate path, but production-verified Level-2 status still requires opt-in live smoke checks, schema monitoring, and provider-permission validation. |
| Phase 3 | Technical indicator library | Complete | MACD, RSI, KDJ, MA, BOLL, and volume chart overlays are supported; backend MACD/KDJ persistence is covered. |
| Phase 3 | AI assistant | Partial / MVP available | `POST /assistant/market` and the instrument-detail AI Market Assistant UI provide traceable, safety-bounded answers from verified daily-bar context, with degraded/no-data fallbacks when context is missing. |

See [docs/manual/user-guide.md](docs/manual/user-guide.md) for user-facing behavior and [docs/runbooks/developer-maintenance.md](docs/runbooks/developer-maintenance.md) for endpoint and provider-maintenance details.

## Tests

```bash
pytest
npm run test:web
```

## MVP 验收

```bash
python scripts/mvp_acceptance.py
```

需先启动 API（默认 `http://127.0.0.1:8000`，可通过 `API_BASE_URL` 覆盖）。

完整清单见 [docs/runbooks/mvp-acceptance.md](docs/runbooks/mvp-acceptance.md)。
