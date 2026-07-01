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
celery -A apps.worker.celery_app worker --loglevel=info
celery -A apps.worker.celery_app beat --loglevel=info
```

6. Start the web app:

```bash
npm install
npm run dev:web
```

Open [http://localhost:3000/en](http://localhost:3000/en).

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/runbooks/local-development.md](docs/runbooks/local-development.md) | Full local setup, env vars, testing |
| [docs/runbooks/mvp-acceptance.md](docs/runbooks/mvp-acceptance.md) | Acceptance checklist |
| [CONTEXT.md](CONTEXT.md) | Domain terminology |
| [docs/superpowers/plans/2026-07-01-priority-5-6-7.md](docs/superpowers/plans/2026-07-01-priority-5-6-7.md) | Latest implementation plan |

## Key features

- **Market data**: yfinance provider (US/HK/CN), Celery scheduled ingestion
- **Analysis pipeline**: indicators, fundamentals, news, AI daily reports
- **Watchlist alerts**: price/RSI rules with trigger history
- **Portfolios**: multi-portfolio CRUD with demo fallback
- **Task runs**: async ingestion/analysis with retry and report linking

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
