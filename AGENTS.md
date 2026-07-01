# AGENTS.md

## Cursor Cloud specific instructions

Stock Analysis Platform — a modular monolith: FastAPI API (`apps/api`), Celery
worker/beat (`apps/worker`), Next.js web app (`apps/web`), shared logic in
`packages/`. Standard setup/run commands live in `README.md` and
`docs/runbooks/local-development.md`; the update script already installs Python
deps into `.venv` and runs `npm install`. Below are only the non-obvious caveats.

### Services & how to run them
Activate the Python venv first for backend commands: `source .venv/bin/activate`.

- Infra (Postgres/TimescaleDB + Redis): `docker compose up -d db redis` (Docker
  daemon must be running: `sudo service docker start`; use `sudo docker ...`).
- Migrations (run after infra is up / on new migrations): `alembic upgrade head`.
- API: `uvicorn apps.api.main:app --reload --port 8000` (http://localhost:8000).
- Web: `npm run dev:web` → http://localhost:3000/en.
- Worker: see the `--include` caveat below.
- Beat (optional, scheduler only): `celery -A apps.worker.celery_app.celery_app beat --loglevel=info`.

### Non-obvious caveats
- Docker is required because migration `0001` needs the TimescaleDB extension
  (`create_hypertable`), so a plain Postgres image will not work.
- `docker-compose.override.yml` sets `NO_TS_TUNE=true` on `db`. Without it, the
  TimescaleDB image's auto-tuner crashes on first boot in this VM (no
  `/sys/fs/cgroup/memory.max`), leaving the db container in `Exited (2)`.
- Celery worker: `autodiscover_tasks(["apps.worker.tasks"])` does NOT register
  the task modules, so a plain worker starts with an empty `[tasks]` list and
  drops dispatched jobs as "unregistered task". Start the worker WITH the task
  modules explicitly included:
  `celery -A apps.worker.celery_app.celery_app worker --include=apps.worker.tasks.ingestion,apps.worker.tasks.reports,apps.worker.tasks.indicators --loglevel=info`
- Provider config: keep `.env` `MARKET_DATA_PROVIDER=yfinance` (the `.env.example`
  default) — some backend tests assert this default. For offline work, pass
  `provider=mock` per request (endpoints accept a `provider` query param) instead
  of changing `.env`. `LLM_PROVIDER=mock` is the default and needs no API key.
- `yfinance` needs internet; `mock` provider works fully offline for E2E/tests.
- Dashboard "采集 / 刷新分析" buttons dispatch async Celery tasks; do NOT fire
  ingestion and analysis for the same market concurrently on a fresh DB — both
  try to insert the same `markets.code` row and one fails with a UniqueViolation.
  Trigger sequentially, or use `/analysis/refresh-sync` (runs in-process, no worker).

### Tests / lint
- Backend tests: `pytest` (needs infra up + migrations). Frontend: `npm run test:web`.
- Lint: `ruff check .` (Python). Note: the repo currently has a few pre-existing
  `ruff` findings and one pre-existing failing web test
  (`apps/web/app/[locale]/watchlist/page.test.tsx`) unrelated to environment setup.
