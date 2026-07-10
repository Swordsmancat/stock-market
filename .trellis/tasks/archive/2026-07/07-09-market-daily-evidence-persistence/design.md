# Market Daily Evidence Persistence MVP Design

## Architecture

Extend the existing local-evidence pattern:

```text
provider-backed daily payload
  -> import service normalizes row identity and dedupe key
  -> market_daily_evidence_events table
  -> citation builder emits market_daily_event:* citations
  -> dashboard / saved briefs / market assistant consume stored citations only
```

The implementation should reuse existing provider-normalized payloads from:

- `packages/services/market_daily_data.py`
- `packages/services/hot_sectors.py`

It should not import InStock runtime modules, scraping proxy/cookie code,
Tornado UI, scheduler jobs, broker APIs, or trading modules.

## Data Model

Add a SQLAlchemy model and Alembic migration for a table named
`market_daily_evidence_events`.

Recommended fields:

- `id`
- `event_type`
- `identity`
- `identity_name`
- `market`
- `trade_date`
- `provider`
- `source`
- `as_of`
- `status`
- `is_citable`
- `payload_json`
- `availability_json`
- `provider_capabilities_json`
- `diagnostics_json`
- `imported_at`
- `updated_at`

Recommended uniqueness:

```text
provider + event_type + identity + market + trade_date
```

Identity examples:

- `stock_fund_flow`: stock symbol
- `limit_up_reason`: stock symbol
- `dragon_tiger_list`: stock symbol
- `block_trade`: stock symbol plus row rank or buyer/seller hash when a symbol
  can have multiple rows for a trade date
- `hot_sector`: sector ID

The stored `payload_json` should contain the normalized item payload, not raw
provider response objects.

## Import Service

Add a service module such as `packages/services/market_daily_evidence.py`.

Core responsibilities:

- call or accept normalized provider payloads for each event type
- skip unavailable/empty provider payloads without fabricating rows
- build deterministic identities and citation IDs
- upsert rows using the deterministic uniqueness rule
- return inserted/updated/skipped counts and sanitized diagnostics
- expose list/citation helpers for stored rows

The service should support fake payload tests without live network access. The
runtime API can default to AkShare-backed provider payloads, but tests should
inject payloads or fake providers.

## API

Add backend routes for manual MVP ingestion and listing. Candidate routes:

```text
POST /market-daily-evidence/import
GET /market-daily-evidence?event_type=...&symbol=...&market=CN&date=YYYY-MM-DD&limit=50
```

Import request fields:

- `date` / `trade_date`
- `market`
- `provider`
- `event_types`
- `limit`

The MVP can stay manual/API-driven. Scheduler automation and bulk historical
backfill are out of scope.

## Citation Contract

Stored citations use:

```text
market_daily_event:<event_type>:<identity>:<trade_date>
```

Citation payload fields:

- `id`
- `label`
- `source`
- `source_type`
- `as_of`
- `provider`
- `excerpt`
- `metadata`

Only stored rows are eligible. Live provider payloads from
`/market-daily-data/*` or `/sectors/hot` remain non-citable.

Update allowed-prefix validation in:

- `packages/services/market_assistant.py`
- `packages/services/market_dashboard.py`
- `packages/services/research_briefs.py`

Only do this together with stored citation assembly so the new prefix does not
make live or invented IDs valid.

## UI / Research Surfaces

Keep the MVP lightweight:

- show stored market daily evidence availability and citations on an existing
  research/evidence surface
- do not build a standalone market-events explorer in this slice
- do not add trading-language summaries or order-oriented actions

Recommended placement: Evidence Center, because it already owns source
readiness, saved research briefs, citation lists, and evidence collection
workflows. AI Research can consume citations through the assistant/brief context
without becoming the operational evidence-management surface.

Minimum visible fields:

- total stored row count
- latest `imported_at` / `updated_at`
- counts by event type
- most recent `market_daily_event:*` citation IDs
- safety copy that only persisted rows are citations

Minimum action:

- "Refresh today's market evidence" posts to the import API with the default MVP
  event types.
- The action should show inserted/updated/skipped counts and sanitized
  diagnostics.
- It should refresh the visible summary after success.
- It should not expose scheduler controls, historical backfill controls, or
  event-type customization in this MVP.

## Decision: Citation Review State

Resolved: imported provider-normalized rows are immediately citable as local
provider-verified evidence.

Successful normalized imports should set `is_citable=true` and can be assembled
into `market_daily_event:*` citations. Failed, unavailable, empty, or skipped
imports do not create citable rows. A manual review state/workflow can be added
later, but it is not part of this MVP.

## Rollback

Rollback requires removing:

- API routes
- service module
- citation integration
- frontend entry
- frontend refresh action
- model/migration references

No existing provider endpoints need to be removed. The migration should be
additive and isolated so existing rows/tables remain untouched.
