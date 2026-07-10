# Market Daily Evidence Contract

> Executable contract for persisting provider-normalized daily market context
> and exposing only stored rows as `market_daily_event:*` citations.

## Scenario: Provider-Verified Daily Market Evidence Persistence

### 1. Scope / Trigger

- Trigger: provider-backed stock fund flow, limit-up, Dragon Tiger List,
  block-trade, and hot-sector rows must become durable AI-citable evidence.
- Scope: `MarketDailyEvidenceEvent` in `packages/domain/models.py`, Alembic
  revision `0013_market_daily_evidence_events`,
  `packages/services/market_daily_evidence.py`, FastAPI router
  `apps/api/routers/market_daily_evidence.py`, dashboard/assistant/research-brief
  citation assembly, the Next proxy under `apps/web/app/api/market-daily-evidence`,
  and the Evidence Center panel.
- Non-goals: citing live provider responses, historical backfill, scheduler
  automation, manual review states, proxy/cookie scraping, trading instructions,
  broker calls, or automatic trading.

### 2. Signatures

- DB table: `market_daily_evidence_events`.
- DB uniqueness: `provider + event_type + identity + market + trade_date`.
- Event types: `stock_fund_flow`, `limit_up_reason`, `dragon_tiger_list`,
  `block_trade`, and `hot_sector`.
- Service import:
  `import_market_daily_evidence(payload, *, session, normalized_payloads=None)`.
- Service list: `list_market_daily_evidence(*, session, event_type=None,
  identity=None, symbol=None, market=None, trade_date=None,
  citable_only=False, limit=50)`.
- Citation list:
  `list_citable_market_daily_evidence_citations(*, session, symbols=None,
  event_types=None, limit=8)`.
- Backend API: `POST /market-daily-evidence/import`.
- Backend API: `GET /market-daily-evidence?event_type=...&symbol=...&market=CN&date=YYYY-MM-DD&citable_only=true&limit=50`.
- Browser proxy: `GET/POST /api/market-daily-evidence`.
- Citation ID:
  `market_daily_event:<event_type>:<identity>:<trade_date>`.

### 3. Contracts

- Stored fields include event/identity/market/date/provider/source/as-of,
  citable status, normalized item payload, availability, provider capabilities,
  sanitized diagnostics, and import/update timestamps.
- Only payloads with `status=ok|degraded`, `data_mode=live|delayed`, a real
  provider, a non-error source, and at least one normalized item are importable.
- `mock`, `static`, fixture, unavailable, empty, and provider-error payloads do
  not create rows and never produce citation IDs.
- Successful normalized rows are immediately stored with `is_citable=true`.
  This MVP has no draft or manual-review state.
- Repeated imports preserve unchanged rows, update changed normalized fields,
  and do not duplicate the deterministic uniqueness key.
- Stock identities use the normalized symbol. Block-trade identities add a
  provider rank or deterministic row fingerprint so multiple same-symbol rows
  can coexist. Hot-sector identities use the normalized sector ID.
- `payload_json` stores the normalized item, never a raw provider response.
  Sensitive fields containing API-key, token, authorization, cookie, password,
  or secret names are removed before storage.
- Dashboard briefs, saved research briefs, and the market assistant add the
  `market_daily_event:` prefix only because their allowed citation collections
  are assembled from stored `MarketDailyEvidenceEvent` rows.
- Evidence Center refresh posts the default event set, reports
  inserted/updated/skipped counts and sanitized diagnostics, then reloads the
  stored summary. It does not expose schedulers, backfill, or custom event
  selection.

### 4. Validation & Error Matrix

- Unsupported market -> HTTP 422; no provider call or row write.
- Unsupported/empty event type set -> HTTP 422 with normalized error details.
- Provider unavailable, empty, mock, or static payload -> import response is
  degraded/skipped; no citable rows are created.
- Normalized row lacks identity or trade date -> row skipped with
  `MARKET_DAILY_EVIDENCE_IDENTITY_INVALID`.
- SQLAlchemy write failure -> rollback the import and return sanitized
  `MARKET_DAILY_EVIDENCE_STORAGE_FAILED`; do not expose SQL, URLs, or secrets.
- Repeated unchanged import -> `skipped` increments and the unique row count
  remains stable.
- Changed row for the same deterministic key -> `updated` increments and the
  existing row/citation ID is preserved.
- LLM cites an unknown `market_daily_event:*` ID -> reject it as
  `CITATION_UNKNOWN_ID` and use deterministic fallback.
- Evidence Center load/import failure -> show an explicit failure state while
  preserving previously loaded stored evidence.

### 5. Good/Base/Bad Cases

- Good: AkShare delayed stock-flow rows are stored, deduped, listed, and cited
  as `market_daily_event:stock_fund_flow:000001:2026-07-10`.
- Good: two block trades for the same symbol/date with different ranks produce
  two stable identities and two stored citations.
- Base: limit-up pool rows have no reason field but are provider-normalized
  delayed rows; they may be stored with the missing reason preserved as null.
- Base: a repeated import has no changed fields; it returns skipped counts and
  does not duplicate rows.
- Bad: the UI constructs a citation ID directly from a live `/market-daily-data/*`
  response.
- Bad: the static hot-sector fixture becomes citable because it has visible
  rows.
- Bad: provider secrets or raw responses are stored in `payload_json` or
  diagnostics.
- Bad: stored events are converted into buy/sell/hold, target-price, sizing, or
  order instructions.

### 6. Tests Required

- Migration tests assert the table, JSON fields, timestamps, and named unique
  constraint exist on SQLite.
- Service tests assert five-event import, dedupe, changed-row update, multiple
  block-trade identities, secret-field sanitization, mock exclusion, symbol
  filtering, and stored-only citation assembly.
- API tests assert POST normalization, GET filters/date alias, import counts,
  stored citation payloads, and HTTP 422 for unsupported event types.
- Assistant/dashboard/research-brief tests assert stored citations are included,
  source-mix counts update, and unknown `market_daily_event:*` IDs fall back.
- Next route tests assert list/import URL, method, body, status, content type,
  and no-store propagation.
- Evidence Center tests assert counts, latest import metadata, citation IDs,
  refresh counts, diagnostics, failed-load behavior, and persisted-only safety
  copy.

### 7. Wrong vs Correct

#### Wrong

```python
live_payload = get_stock_fund_flow_payload(provider_name="akshare")
citations = [
    {"id": f"market_daily_event:stock_fund_flow:{row['symbol']}:latest"}
    for row in live_payload["items"]
]
```

This bypasses persistence, stable dates, dedupe, provider-mode validation, and
the stored-evidence citation gate.

#### Correct

```python
import_market_daily_evidence(import_input, session=session)
citations = list_citable_market_daily_evidence_citations(
    session=session,
    symbols=["000001"],
)
```

The import service owns provider validation and storage; citation consumers read
only persisted, citable rows.
