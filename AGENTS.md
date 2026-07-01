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
- Web: export the API URL first, then start (see web env caveat below):
  `export API_BASE_URL=http://127.0.0.1:8000 NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 NEXT_PUBLIC_MARKET_DATA_PROVIDER=mock && npm run dev:web`
  → http://localhost:3000/en.
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
- Web env caveat: `next dev` runs from `apps/web/`, so it does NOT read the repo
  root `.env`. Without an API URL in its own environment, `apps/web/lib/backend-api.ts`
  falls back to `http://127.0.0.1:8001` (wrong port) and the dashboard shows a
  "Cannot reach the API" banner. Export `API_BASE_URL`/`NEXT_PUBLIC_API_BASE_URL`
  for the web process (as shown above). Use `127.0.0.1`, not `localhost`: the API
  (`uvicorn --host 0.0.0.0`) listens on IPv4 only, and some clients resolve
  `localhost` to IPv6 `::1` first, which is refused.
- Dashboard "采集 / 刷新分析" buttons dispatch async Celery tasks; do NOT fire
  ingestion and analysis for the same market concurrently on a fresh DB — both
  try to insert the same `markets.code` row and one fails with a UniqueViolation.
  Trigger sequentially, or use `/analysis/refresh-sync` (runs in-process, no worker).

### Tests / lint
- Backend tests: `pytest` (needs infra up + migrations). Frontend: `npm run test:web`.
- Lint: `ruff check .` (Python). Note: the repo currently has a few pre-existing
  `ruff` findings and one pre-existing failing web test
  (`apps/web/app/[locale]/watchlist/page.test.tsx`) unrelated to environment setup.
