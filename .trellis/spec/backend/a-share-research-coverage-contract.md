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
