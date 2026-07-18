# Crawler execution monitor design

## Architecture

Add a read-only `GET /crawler-monitor` endpoint backed by a dedicated service. The service owns a static tuple of curated pipeline definitions and queries a bounded recent TaskRun window once. It matches each row in Python by exact task name and a small equality selector over `input_json`, avoiding PostgreSQL-specific JSON SQL and preserving SQLite tests.

The endpoint must not reuse TaskRun helpers that call `expire_stale_task_runs`, because expiry is a database mutation. It serializes only an allowlisted projection.

## Pipeline definitions

Each definition contains a stable id, translation key, task name, selector, scope/provider labels, expected cadence, and freshness/stall thresholds. Initial definitions:

- `market_cn`, `market_us`, `market_hk`: `ingestion.ingest_market_data` selected by `market`.
- `universe_cn`: `ingestion.sync_instrument_universe`, selected by `market=CN`.
- `evidence_incremental`: `ingestion.backfill_a_share_research_evidence`, selected by `run_kind=incremental`.
- `fundamental_shard`: the same task selected by `run_kind=fundamental_shard`.
- `official_disclosures`: `ingestion.ingest_watchlist_official_disclosures`.

## Status calculation

The newest matching TaskRun is authoritative.

- No match: `not_recorded`.
- Latest `running` with heartbeat/start newer than the stall threshold: `running`.
- Latest `running` with stale heartbeat/start: `stalled`.
- Latest `failed`: `failed`.
- Latest `succeeded` within its freshness window: `healthy`.
- Latest `succeeded` outside its freshness window: `overdue`.
- Unknown terminal status: `failed` with a bounded diagnostic code, never a raw payload.

Summary counts are derived from the seven projected rows. Recent failures count matching failed rows within 24 hours. Progress is accepted only when phase/message are bounded strings and current/total are finite non-negative integers; message is clipped before serialization.

## Frontend

The localized server page validates the response through a shared TypeScript decoder. A client control refreshes the route every 30 seconds and exposes a refresh icon with tooltip/accessible label.

Desktop layout uses a wrapping status band followed by a dense table. Mobile stacks one unframed pipeline row per item with no horizontal page overflow. Status uses a semantic icon, localized text, and theme tokens rather than color alone. Progress bars have stable dimensions and an accessible label.

## Failure and compatibility

- API failure renders a localized page failure state; it is not an empty pipeline list.
- Missing TaskRuns render seven `not_recorded` pipeline rows because definitions are part of the contract.
- Existing `/task-runs` endpoints and worker schedules are unchanged.
- No migration is required.
- The endpoint is additive and can be rolled back independently.

## Verification

Use SQLite service/API tests, Vitest decoder/page/control tests, full Ruff/TypeScript suites, and the running Docker stack. Confirm current production evidence shows the active fundamental shard and that desktop/mobile light/dark layouts have no horizontal overflow or console errors.
