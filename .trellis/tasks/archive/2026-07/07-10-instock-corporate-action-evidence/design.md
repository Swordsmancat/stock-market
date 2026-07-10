# InStock Comprehensive A-share Research Coverage Design

## Problem Statement

The platform can screen stored instruments, but the current CN provider exposes
only a tiny fixture universe and the screener truncates candidates to the first
100 instruments before evaluation. The AI Research surface then builds its
candidate list primarily from watchlist/followed symbols, while the market
assistant analyzes one symbol at a time. This creates discovery bias even when
individual analysis is evidence-safe.

The minimum durable correction is a breadth-first pipeline:

1. synchronize a complete provider-backed A-share instrument universe;
2. evaluate every eligible stored candidate with bulk-loaded local evidence;
3. expose named, transparent criteria profiles and coverage diagnostics;
4. let AI explain only the deterministic shortlist and its allowed citations;
5. enrich the same universe with persisted corporate-action evidence in
   bounded jobs.

## Fundamental Invariants

- Candidate breadth and evidence completeness are different metrics.
- Missing evidence is a coverage gap, not a failed investment conclusion.
- Selection never fans out to live providers.
- Result limits bound returned matches, not evaluated candidates.
- A failed or empty universe refresh never destroys the last good universe.
- Watchlist membership may prioritize collection but never defines the default
  market universe.
- The LLM may explain a supplied shortlist but cannot add symbols, change the
  deterministic ranking, invent citations, or issue trading instructions.

## Architecture and Data Flow

```text
AkShare universe endpoint
  -> InstrumentUniverseProvider normalization
  -> universe sync service
  -> Market / Exchange / Instrument + InstrumentUniverseSync
  -> bulk local evidence loader
  -> deterministic selection profile and ranking
  -> bounded shortlist + coverage + citations
  -> deterministic/LLM explanation with symbol and citation validation
  -> AI Research UI

AkShare corporate-action endpoints
  -> bounded corporate-action job
  -> normalized dividend/bonus and rights-allotment rows
  -> MarketDailyEvidenceEvent
  -> shortlist citation enrichment + Evidence Center counts
```

## Provider Boundary

### Universe provider

Add an additive `InstrumentUniverseProvider` protocol and normalized snapshot
types under `packages/providers/base.py`. The new method is separate from the
existing `ProviderAdapter.fetch_instruments()` path.

This separation is required because `get_market_snapshot()` currently fetches
bars for every instrument returned by `fetch_instruments()`. Replacing the
AkShare fixture with 5,000+ real instruments inside that old method would turn
existing scheduled market ingestion into an accidental full-market bar crawl.

The AkShare universe adapter uses an injected downloader whose runtime default
calls `stock_info_a_code_name()`. It normalizes:

- six-digit symbol;
- provider name;
- market `CN`;
- exchange inferred from reviewed code prefixes (`SSE`, `SZSE`, `BSE`), with
  unknown prefixes preserved as a degraded diagnostic rather than guessed;
- asset type `stock`;
- currency `CNY`;
- source and retrieval/as-of timestamps.

Tests inject DataFrames and never use the live network.

### Corporate-action provider

Add a focused corporate-action provider/service boundary rather than placing
AkShare calls in routers or the evidence importer.

- Dividend/bonus-transfer: use a report-period bulk endpoint when available,
  with per-symbol history as an explicit fallback only for bounded jobs.
- Rights allotment: use per-symbol calls in deterministic batches.
- Provider output includes normalized items, availability, capability metadata,
  as-of time, data mode, source, and sanitized diagnostics.
- Empty, mock, failed, or schema-incompatible output remains non-citable.

## Persistence Design

### Instrument provenance

Add nullable columns to `Instrument`:

- `universe_provider` — identifies rows managed by a successful universe sync;
- `universe_synced_at` — last successful snapshot in which the row appeared.

Existing/manual instruments keep `universe_provider=null` and are never
deactivated by provider reconciliation.

### Universe sync history

Add `InstrumentUniverseSync` / `instrument_universe_syncs` with:

- `id`, `market`, `provider`, `source`, `as_of`, `status`;
- total/inserted/updated/unchanged/reactivated/deactivated counts;
- normalized availability and sanitized diagnostics JSON;
- `created_at`.

The model provides durable freshness and reconciliation history without
overloading `Market` or `TaskRun`.

### Reconciliation algorithm

1. Fetch and fully normalize the provider snapshot before writing.
2. Reject empty or invalid snapshots without changing instrument activity.
3. Upsert market/exchange/instrument identities in one transaction.
4. Mark seen rows active and set provider/sync timestamp.
5. Deactivate only active `CN/stock` rows managed by the same universe provider
   that are absent from the successful complete snapshot.
6. Commit the instrument changes and a succeeded sync-history row together.
7. On database failure, roll back all reconciliation changes.

### TaskRun progress

Do not add a second job table. Add `update_task_run_progress(...)` to reuse the
existing nullable `TaskRun.result_json` while status is `running`.

Progress snapshots use a stable shape:

```json
{
  "status": "running",
  "phase": "reconcile_universe",
  "processed": 1200,
  "total": 5300,
  "succeeded": 1197,
  "failed": 3,
  "cursor": 1200,
  "diagnostics": []
}
```

The final `finish_task_run()` payload replaces the progress snapshot. Retry
inputs preserve safe cursor/report-period fields, not secrets.

### Corporate-action evidence

Reuse `MarketDailyEvidenceEvent`; no separate event table is needed. Add event
types:

- `dividend_bonus`;
- `rights_allotment`.

Canonical event date uses the most specific verified implementation date
available, then record/ex-right/payment date, then announcement/report date.
Identity includes symbol plus a deterministic normalized event fingerprint so
multiple plans for one symbol/date remain distinct. The existing table unique
key and citation prefix remain backward compatible.

## Full-Universe Selection Design

### Candidate loading

Remove the pre-evaluation `MAX_SCREENING_SYMBOLS=100` truncation. Candidate
scope still supports explicit symbols, market, asset type, and watchlist-only.
The response `limit` is applied only after all eligible candidates are scored.

### Bulk evidence loading

Avoid per-instrument queries by loading evidence maps before evaluation:

- latest `DailyBar` per instrument through a max-date subquery/join;
- all `TechnicalIndicator` rows at the latest `1d` as-of per instrument through
  a grouped subquery/join;
- latest `FundamentalSnapshot` per symbol through a max-as-of subquery/join;
- news counts and latest joined sentiment only when news criteria are active;
- citable corporate-action events only for returned shortlist symbols.

The evaluator becomes a pure function over an instrument plus its evidence
bundle. Existing criterion behavior and citation IDs remain unchanged.

### Coverage payload

Add:

```json
{
  "coverage": {
    "universe_count": 5300,
    "evaluated_count": 5300,
    "evidence_complete_count": 1840,
    "insufficient_evidence_count": 3460,
    "missing_by_source": {
      "daily_bar": 100,
      "fundamentals": 2200,
      "technical_indicators": 1300,
      "news": 900
    }
  }
}
```

Coverage diagnostics are aggregated. The API must not emit thousands of
duplicate per-symbol diagnostic messages; returned shortlist items may retain
their focused diagnostics, while coverage summary owns market-wide gaps.

## Named Selection Profiles

Define profiles once in the backend and expose them through
`GET /stock-selection/profiles`:

- `balanced_research`;
- `quality_value`;
- `trend_liquidity`.

Each profile returns its label key, description key, criteria fields, numeric
defaults, and disclaimer. `POST /stock-selection/discover` requires a profile
and accepts supported explicit overrides. The response echoes the effective
criteria so no threshold is hidden. Existing `GET /stock-selection/screen`
continues to support explicit criteria and remains backward compatible.

Profile values are research defaults, not recommendations. Frontend labels are
localized; backend field names remain stable English contract keys.

## AI Shortlist Explanation

Add a dedicated stock-discovery AI module/service rather than stretching the
single-symbol market assistant request contract.

`POST /stock-selection/discover` flow:

1. normalize profile and overrides;
2. run deterministic full-universe screening;
3. cap the explanation shortlist to a bounded size;
4. collect only citations already attached to shortlist evidence plus stored
   citable corporate-action events for those symbols;
5. generate deterministic explanation by default/fallback;
6. optionally call the configured OpenAI-compatible provider;
7. validate every inline citation ID and every six-digit candidate symbol in
   generated output against the supplied shortlist;
8. fall back with `CITATION_UNKNOWN_ID` or `CANDIDATE_UNKNOWN_SYMBOL` when
   validation fails.

Response shape is additive and explicit:

- `profile`, `effective_criteria`;
- `selection` including shortlist and coverage;
- `analysis_markdown`;
- `citations`, `diagnostics`, `model`, and `safety`.

No selection result is automatically persisted as evidence in this MVP.

## API and Worker Surface

- `POST /ingestion/instrument-universe` — enqueue universe sync TaskRun.
- Task: `ingestion.sync_instrument_universe`.
- `GET /stock-selection/universe-status` — latest successful sync and current
  active/coverage counts.
- `GET /stock-selection/profiles` — named profile contracts.
- Existing `GET /stock-selection/screen` — full eligible local scan.
- `POST /stock-selection/discover` — deterministic shortlist plus explanation.
- `POST /market-daily-evidence/corporate-actions/import` or an equivalent
  task-enqueue route — bounded report-period/symbol-batch enrichment.

Routers remain thin and map validation/provider errors using existing patterns.

## Frontend Design

Extend the existing AI Research route, not the homepage:

- universe status card: provider, source, last successful sync, active count,
  freshness, and failure-safe state;
- refresh action that creates a TaskRun and links to existing task-run detail;
- named profile selector with visible/editable supported criteria;
- discovery action with loading, failure, empty, and success states;
- shortlist table showing rank, score, matched rules, evidence coverage, and
  source gaps;
- AI explanation and allowed citation badges;
- action to move a shortlist symbol into the existing single-symbol assistant,
  without silently adding it to the watchlist.

Evidence Center continues to own persisted corporate-action counts and citation
history. Add the two event labels and import diagnostics there rather than
duplicating an event explorer on AI Research.

Browser mutations use Next route proxies and `router.refresh()`/existing polling
patterns. All visible text is added to both locale catalogs.

## Compatibility and Migration

- Alembic revision `0014` adds nullable instrument provenance fields and the
  universe-sync history table with PostgreSQL/SQLite-compatible types.
- Existing instrument rows require no backfill and remain active/manual.
- Existing provider `fetch_instruments()` and market snapshot behavior are not
  changed to return the full universe.
- Existing explicit-symbol and watchlist-only selection calls retain behavior,
  except that unbounded stored-universe calls no longer truncate before
  evaluation.
- Existing five market-daily event types and citation consumers remain valid.
- Frontend types treat new response fields as additive where old payloads may be
  encountered.

## Performance and Operational Boundaries

- Universe discovery is one provider list call, not one call per symbol.
- Selection uses bulk SQL queries and never provider fan-out.
- LLM context contains only the bounded shortlist and compact coverage summary.
- Corporate-action per-symbol calls use deterministic batch size/cursor and
  partial-success diagnostics.
- Repeated refreshes upsert and reconcile instead of deleting/reinserting.
- No automatic daily schedule is added until manual runtime evidence confirms
  provider stability and execution time.

## Failure and Security Matrix

- Universe provider exception/empty/schema drift -> failed/degraded TaskRun,
  last good universe untouched.
- Partial normalization -> invalid rows skipped with counts; snapshot is
  considered complete only when provider response itself is valid and nonempty.
- DB write failure -> rollback; no partial deactivation.
- Selection evidence gaps -> aggregate coverage diagnostics; no fabricated
  values or negative conclusion.
- LLM unavailable/empty/error -> deterministic explanation.
- Unknown LLM citation/symbol -> deterministic fallback.
- Corporate-action provider partial failure -> successful prior rows preserved,
  failed symbols/cursor reported for retry.
- Provider responses, cookies, keys, stack traces, and hidden prompts are never
  stored or returned.

## Rollout and Rollback

1. Ship schema and backend universe sync behind explicit API action.
2. Verify fake-provider tests and optional manual AkShare smoke separately.
3. Ship full-universe selection and coverage diagnostics.
4. Ship AI Research profile/discovery UI.
5. Ship bounded corporate-action enrichment and evidence labels.

Rollback is additive: stop invoking new jobs/routes, leave existing instruments
active, and downgrade `0014` only when stored sync history/provenance can be
discarded. Never roll back by deleting the instrument universe or market-daily
evidence rows through application code.

## Validation Strategy

- migration/model tests for revision `0014`;
- provider parser tests with injected DataFrames;
- universe reconciliation/failure-preservation tests;
- TaskRun progress/worker/dispatch/API tests;
- stock-selection regression with more than 100 instruments and query-count or
  bulk-loader assertions;
- profile/override/coverage/AI citation+symbol validation tests;
- corporate-action normalization/dedupe/import/citation tests;
- Next proxy, AI Research component/page, Evidence Center, and localization
  tests;
- full Python and Web suites, ruff, TypeScript, locale JSON parsing, Trellis
  validation, and `git diff --check`.
