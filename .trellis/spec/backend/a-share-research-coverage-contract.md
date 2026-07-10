# Comprehensive A-share Research Coverage Contract

## Scenario: Full-Universe Screening and Corporate-Action Evidence

### 1. Scope / Trigger

- Trigger: AI stock discovery must start from the complete locally synchronized
  active A-share universe rather than a watchlist-sized sample.
- Scope: the additive AkShare universe and corporate-action provider contracts,
  `Instrument` provenance, `InstrumentUniverseSync`, TaskRun-backed ingestion,
  bulk local screening, transparent profiles, validated AI explanation,
  corporate-action evidence, FastAPI/Next proxies, AI Research, and Evidence
  Center surfaces.
- Non-goals: InStock runtime/MySQL/Tornado import, proxy/cookie scraping,
  natural-language-to-screening-rule generation, broker connectivity, order
  intents, portfolio weights, or automated trading.

### 2. Signatures

- DB:
  - nullable `instruments.universe_provider`
  - nullable `instruments.universe_synced_at`
  - `instrument_universe_syncs` from Alembic revision `0014`
- Provider:
  - `InstrumentUniverseProvider.fetch_instrument_universe(market)`
  - `CorporateActionProvider.fetch_corporate_actions(event_type,
    report_period, symbols)`
- Services:
  - `sync_instrument_universe(...)`
  - `get_instrument_universe_status(...)`
  - `screen_local_stock_selection(...)`
  - `resolve_stock_selection_profile(profile_id, overrides)`
  - `discover_local_stocks(...)`
  - `sync_corporate_action_evidence(CorporateActionSyncInput, ...)`
- Tasks:
  - `ingestion.sync_instrument_universe`
  - `ingestion.sync_corporate_actions`
- APIs:
  - `POST /ingestion/instrument-universe`
  - `GET /ingestion/instrument-universe/status`
  - `GET /stock-selection/universe-status`
  - `GET /stock-selection/profiles`
  - `POST /stock-selection/discover`
  - `POST /ingestion/corporate-actions`
- Web proxies mirror these mutations/queries under `/api/...`.

### 3. Contracts

- The universe path is separate from `ProviderAdapter.fetch_instruments()`.
  The old market snapshot path may still return a small fixture and fetch bars;
  it must never receive the full A-share universe implicitly.
- A complete valid universe snapshot may insert, update, reactivate, and
  deactivate rows managed by that provider. An incomplete, empty, schema-bad,
  or failed refresh must preserve the last good active universe and manual rows.
- `InstrumentUniverseSync` stores source, as-of, status, reconciliation counts,
  availability, sanitized diagnostics, and created time for auditability.
- Full-universe screening has no pre-evaluation 100-symbol cap. Returned items
  remain bounded to `1..100`; discovery shortlists remain bounded to `1..20`.
- Latest bars, indicators, fundamentals, and conditional news/sentiment are
  loaded in bulk. Do not add per-instrument evidence queries.
- Full-universe results include candidate/evaluated/matched/returned counts and
  source coverage ratios. Large scans aggregate diagnostics; explicit/small
  scans may retain symbol-level diagnostics.
- Profiles `balanced_research`, `quality_value`, and `trend_liquidity` expose
  visible defaults and supported overrides. Every active criterion is ANDed;
  missing evidence is not a match.
- `/stock-selection/discover` runs deterministic screening first. AI may explain
  only the fixed shortlist and ranking. Unknown inline citation IDs or backtick
  candidate symbols force the deterministic fallback.
- Corporate-action batches are deterministic by normalized sorted symbols,
  `report_period`, `cursor`, `batch_size<=100`, and event types
  `dividend_bonus` / `rights_allotment`. Per-symbol/provider failures preserve
  successful rows and emit retry diagnostics.
- Corporate actions become citable only after persistence in
  `market_daily_evidence_events`. Their identity includes a normalized
  fingerprint so distinct same-symbol/same-date actions do not overwrite one
  another.
- Every payload and UI keeps the research-only, no-investment-advice, and
  no-automated-trading boundary.

### 4. Validation & Error Matrix

- Universe market other than `CN` or provider other than `akshare` -> `ValueError`
  / HTTP 400; no provider call for unsupported market.
- Universe provider exception -> failed sync history row, sanitized exception
  type, old active universe preserved.
- Empty/incomplete universe -> no managed-row deactivation.
- No selection criteria -> `NO_SELECTION_CRITERIA` / HTTP 400.
- More than 100 candidates -> all candidates evaluated; only response items are
  limited.
- Unknown profile or override key -> `ValueError` / HTTP 400.
- LLM unavailable, disabled, empty, or raises -> deterministic explanation.
- LLM mentions unknown citation/symbol -> diagnostic plus deterministic fallback;
  shortlist data remains unchanged.
- Corporate-action cursor past the universe -> `status=no_data`.
- One corporate-action event/symbol fails -> `status=partial`, successful
  evidence committed, failed event/symbol listed under `retry`.
- All corporate-action event providers fail -> failed TaskRun with no fabricated
  citable rows.
- Mock/static/unavailable corporate rows -> never citable.

### 5. Good / Base / Bad Cases

- Good: a 5,000+ row CN universe sync succeeds, screening evaluates all active
  rows in bulk, and a match after ordinal 100 ranks into the bounded shortlist.
- Good: one rights-allotment symbol fails while dividends and other rights rows
  persist with stable `market_daily_event:*` citations and retry metadata.
- Base: no LLM key is configured; profile screening and deterministic explanation
  still return a complete auditable research result.
- Base: an incomplete universe refresh updates seen rows but deactivates none.
- Bad: using `fetch_instruments()` for the full universe causes the old snapshot
  ingestion to fetch bars for every A-share symbol.
- Bad: applying `.limit(100)` before evidence evaluation makes AI discovery
  silently incomplete.
- Bad: an LLM adds a symbol, changes ranking, or invents a citation.
- Bad: one corporate-action failure rolls back or deletes other successful
  evidence rows.

### 6. Tests Required

- Provider tests: multi-exchange universe mapping, duplicates, malformed/empty
  frames, dividend normalization, rights partial failure, and no live network.
- Service tests: safe universe reconciliation, >100 candidate regression,
  constant-query bulk screening, coverage, profile resolution, LLM validation,
  cursor continuation, partial corporate-action success, and citable identities.
- Migration tests: revision `0014` columns/table on SQLite-compatible execution.
- API/worker/dispatch tests: normalized TaskRun inputs, progress, retry, status,
  and synchronous Celery coverage.
- Web tests: proxies, full-universe discovery states, editable parameters,
  coverage, shortlist, explanation/citations/diagnostics, TaskRun links, symbol
  handoff, and Evidence Center corporate-action labels.
- Gates: touched-file ruff, TypeScript `--noEmit`, locale JSON parse, full pytest,
  full Vitest, Trellis validation, and `git diff --check`.

### 7. Wrong vs Correct

#### Wrong

```python
candidates = query.order_by(Instrument.symbol).limit(100).all()
for candidate in candidates:
    latest_bar = session.query(DailyBar).filter_by(instrument_id=candidate.id).first()
```

This silently truncates the research universe and creates N+1 evidence queries.

#### Correct

```python
candidates = query.order_by(Instrument.symbol).all()
evidence = _load_selection_evidence(session=session, instruments=candidates, include_news=False)
```

All in-scope candidates are evaluated against bulk-loaded local evidence; only
the final ranked response is bounded.

## Scenario: Resumable Full-Market Evidence Backfill

### 1. Scope / Trigger

- Trigger: the synchronized A-share identity universe must receive enough stored
  daily bars, fundamentals, and technical indicators for full-scope discovery.
- Scope: `ResearchEvidenceBackfill`, TaskRun heartbeat, AkShare phase batches,
  coverage projection, FastAPI routes, Celery dispatch/Beat, and focused tests.
- Non-goals: Web controls, live acceptance execution, multi-provider merge,
  filings, backtests, or trading.

### 2. Signatures

- DB: `research_evidence_backfills` and nullable `task_runs.heartbeat_at` from
  Alembic revision `0015`.
- Service: `BackfillRequest`, `create_backfill_run(...)`,
  `execute_backfill_run(...)`, `create_resume_backfill_run(...)`,
  `create_retry_failed_backfill_run(...)`, `request_cancel_backfill(...)`, and
  `get_evidence_coverage(...)`.
- Task: `ingestion.backfill_a_share_research_evidence`.
- API: `POST /ingestion/a-share-evidence-backfills`, get/resume/retry-failed/
  cancel routes by run ID, and `GET /stock-selection/evidence-coverage`.
- Schedule task: `ingestion.schedule_a_share_evidence_backfill`.
- Settings: `A_SHARE_BACKFILL_REQUEST_DELAY_MS` (default 250),
  `A_SHARE_BACKFILL_MAX_TRANSIENT_ATTEMPTS` (default 3), and
  `A_SHARE_BACKFILL_RETRY_BASE_SECONDS` (default 1.0).

### 3. Contracts

- A run freezes its normalized `(exchange, symbol)` scope in
  `scope_symbols_json`; a later universe sync cannot reinterpret its cursor.
- Network phases `daily_bars` and `fundamentals` are separate from local
  `technical_indicators`. Default batch size is 25 and public bounds are 1-100.
- Baselines default to 18 calendar months; incrementals default to a 10-day
  overlap. Canary cohorts include SSE/SZSE/BSE; fundamental shards use stable
  ordinal modulo five.
- Cursor/counters/retry sets/diagnostics/heartbeat commit after every bounded
  batch. Replaying an interrupted batch is safe through existing evidence
  identities.
- Provider phases are sequential by default, apply configured pacing, and retry
  only transient timeout/rate-limit/unavailable failures with bounded
  exponential backoff. Valid no-data is not retried in-place.
- AkShare is explicit. Valid empty results, provider errors, schema errors,
  timeouts/rate limits, and insufficient local bars remain distinct; no other
  provider is selected automatically.
- Coverage uses a bounded number of aggregate queries. Ready means at least 35
  fresh bars, latest-date `ma`/`rsi`/`mfi`, or a recent complete PE/revenue-
  growth/net-margin snapshot. Gates are 95%, 90%, and 80%, respectively.
- TaskRun stale detection uses `heartbeat_at` with `started_at` fallback for old
  rows. Cooperative cancellation stops at a checkpoint and preserves writes.
- Celery timezone is `Asia/Shanghai`; weekday 18:30 refreshes bars/indicators,
  and a later weekday schedule rotates fundamental shards. Active-run overlap
  returns `already_running` rather than duplicating work.

### 4. Validation & Error Matrix

- Market other than CN, provider other than AkShare, unsupported kind/run kind,
  invalid dates, or batch outside 1-100 -> `ValueError` / HTTP 400.
- No active instruments -> no dispatch and HTTP 400.
- Unknown run ID -> HTTP 404.
- Active same-market/provider run -> `already_running`; no second task.
- Provider exception -> sanitized failed outcome plus retry symbol; prior rows
  and checkpoint remain.
- Valid empty provider response -> `no_data`, never a provider failure or pass.
- Indicator history too short -> `insufficient_data`, not fabricated output.
- Healthy heartbeat newer than cutoff -> running TaskRun remains active; null or
  stale heartbeat falls back/expires as documented.

### 5. Good / Base / Bad Cases

- Good: a worker commits 25 symbols, updates heartbeat/cursor, crashes, and a
  lineage-linked resume safely replays at most the uncheckpointed batch.
- Good: 5,000 instruments produce coverage with constant aggregate queries and
  exchange-level gaps.
- Base: some new listings have no 35-row history; the run completes with an
  explicit gap and thresholds decide readiness.
- Bad: a provider timeout is converted to `no_data`, removing it from retry.
- Bad: the cursor is recomputed from the current active universe after sync.
- Bad: coverage loads every DailyBar row or queries once per instrument.

### 6. Tests Required

- Migration/model tests assert revision `0015`, frozen scope JSON, and heartbeat.
- Service tests assert deterministic canary/shards, partial success, resume,
  retry sets, cancellation, idempotent replay boundaries, and sanitized errors.
- Coverage tests assert field/date readiness, exchange breakdown, thresholds,
  and no more than five SELECTs for a 150-instrument fixture.
- API/dispatch/worker tests assert TaskRun linkage and synchronous completion.
- Schedule tests assert `Asia/Shanghai`, 18:30 incrementals, and shard kwargs.
- Full backend pytest, touched Ruff, Trellis validation, and `git diff --check`
  are required.

### 7. Wrong vs Correct

#### Wrong

```python
for instrument in instruments:
    bars = session.query(DailyBar).filter_by(instrument_id=instrument.id).all()
```

This creates N+1 queries and loads the full history to calculate coverage.

#### Correct

```python
rows = (
    session.query(DailyBar.instrument_id, func.count(), func.max(DailyBar.trade_date))
    .filter(DailyBar.instrument_id.in_(instrument_ids))
    .group_by(DailyBar.instrument_id)
    .all()
)
```

One aggregate query returns the readiness inputs for the complete scope.
