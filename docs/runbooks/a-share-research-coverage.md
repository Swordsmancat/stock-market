# A-share Research Coverage Runbook

This runbook covers the complete local A-share universe, deterministic
full-universe screening, AI shortlist explanation, and persisted corporate
actions. These features are research workflows only and do not place trades.

## User workflow

1. Open **AI Research**.
2. Review the universe status, active/provider-managed counts, and latest sync.
3. Click **Refresh A-share universe** when the local universe is stale. Follow
   the linked TaskRun until it succeeds or reports diagnostics.
4. Choose `balanced_research`, `quality_value`, or `trend_liquidity`.
5. Review and edit the visible criteria, then run full-universe discovery.
6. Inspect candidate/evidence coverage, the deterministic shortlist, stored
   citation IDs, diagnostics, and the AI or deterministic explanation.
7. Use **Use in desk** to pass a candidate to the existing single-symbol AI
   Research Desk.

The screener requires every active criterion to match. Missing bars,
fundamentals, indicators, or requested news evidence are shown as gaps; they are
never inferred as a pass. AI does not add candidates or change their ranking.

In **Evidence Center**, choose a corporate-action report period and queue a
batch. The first task processes up to 50 sorted symbols by default. Use the
TaskRun result's `next_cursor` to continue until `complete=true`. Successful
dividend/bonus or rights rows remain stored even when another symbol/event
fails.

## Operator workflow

Run migrations before the first universe sync:

```bash
alembic upgrade head
```

### Isolated real-provider acceptance

Never run mutating acceptance against the normal `stock` database. The
acceptance stack uses Compose project `stock-acceptance`, database
`stock_acceptance`, isolated volumes, API port `18000`, Web port `13000`,
PostgreSQL port `55432`, and Redis port `56379`.

Run the read-only AkShare universe and daily-bar preflight before starting the
stack (and therefore before migrations can write):

```bash
python scripts/a_share_live_acceptance.py --phase preflight --real-network
```

Abort when either preflight check fails. Provider-wide network, empty-universe,
schema, or missing-exchange failures must not be reclassified as valid no-data.

Validate and start the isolated runtime:

```bash
docker compose -p stock-acceptance -f docker-compose.acceptance.yml config
docker compose -p stock-acceptance -f docker-compose.acceptance.yml up -d --build
docker compose -p stock-acceptance -f docker-compose.acceptance.yml ps
```

Run the guarded 50-symbol canary. Both write guards and the exact database name
are mandatory; the runner also verifies `/health/runtime` reports
`APP_ENV=acceptance`, `stock_acceptance`, and `Asia/Shanghai` before dispatch:

```bash
python scripts/a_share_live_acceptance.py \
  --phase canary \
  --real-network \
  --confirm-acceptance-writes \
  --database-url postgresql+psycopg://stock:stock@127.0.0.1:55432/stock_acceptance
```

Only after the canary is usable should an operator start the 18-month baseline:

```bash
python scripts/a_share_live_acceptance.py \
  --phase baseline \
  --real-network \
  --confirm-acceptance-writes \
  --timeout-seconds 21600 \
  --database-url postgresql+psycopg://stock:stock@127.0.0.1:55432/stock_acceptance
```

The runner writes bounded, sanitized JSON evidence under the active Trellis
task's `evidence/` directory. It redacts connection URLs, authorization/cookie
fields, token/secret-like keys, and bearer values; it never writes raw provider
payloads or exception text.

Stop services while retaining checkpoints/evidence:

```bash
docker compose -p stock-acceptance -f docker-compose.acceptance.yml down
```

Destructive cleanup is a separate, explicit action and removes only
project-prefixed acceptance volumes:

```bash
docker compose -p stock-acceptance -f docker-compose.acceptance.yml down --volumes
```

Use `cancel`, `resume`, and `retry-failed` on the recorded backfill ID instead
of deleting partial evidence. On a provider-wide schema/rate failure, cancel at
the next checkpoint, retain the retry set, and stop rather than flooding
retries.

Start API, worker, and Redis, then enqueue the universe:

```text
POST /ingestion/instrument-universe?market=CN&provider=akshare
GET  /stock-selection/universe-status?market=CN&provider=akshare
```

Corporate-action batch example:

```json
POST /ingestion/corporate-actions
{
  "report_period": "2025-12-31",
  "market": "CN",
  "provider": "akshare",
  "symbols": [],
  "event_types": ["dividend_bonus", "rights_allotment"],
  "cursor": 0,
  "batch_size": 50
}
```

An empty `symbols` list uses sorted active CN stock instruments. Repeat with the
returned `next_cursor`. Keep the same report period, event types, and batch size
for deterministic continuation.

### Research evidence backfill

After a successful universe sync, start a bounded canary before the baseline:

```json
POST /ingestion/a-share-evidence-backfills
{
  "run_kind": "canary",
  "market": "CN",
  "provider": "akshare",
  "cohort_size": 50,
  "batch_size": 25,
  "evidence_kinds": ["daily_bars", "fundamentals", "technical_indicators"]
}
```

Use the returned backfill ID with the get, `resume`, `retry-failed`, or `cancel`
routes under `/ingestion/a-share-evidence-backfills/{run_id}`. Cancellation is
cooperative and preserves completed batches. A baseline without explicit dates
uses 18 calendar months; an incremental uses a 10-day overlap. Check current
stored readiness with:

```text
GET /stock-selection/evidence-coverage?market=CN&provider=akshare
```

The readiness gates are 95% daily bars, 90% critical indicators, and 80%
critical fundamentals, with non-empty SSE/SZSE/BSE coverage. A completed worker
run can still leave the research store below these gates; the coverage response
then remains `needs_attention`.

Celery runs in `Asia/Shanghai`. Weekday bars/indicators are scheduled at 18:30
with a 10-day overlap, and fundamentals rotate through deterministic fifths of
the universe. If another AkShare backfill is active, the schedule reports
`already_running` instead of creating overlapping provider load.

Provider pacing defaults to 250 ms between network symbols with at most three
transient attempts and a 1-second exponential-backoff base. Operators can tune
`A_SHARE_BACKFILL_REQUEST_DELAY_MS`,
`A_SHARE_BACKFILL_MAX_TRANSIENT_ATTEMPTS`, and
`A_SHARE_BACKFILL_RETRY_BASE_SECONDS`; lowering pacing can increase provider
throttling and must not change valid no-data into a retryable failure.

## Completeness and failure semantics

- Universe source: `akshare.stock_info_a_code_name`.
- Exchanges: SSE, SZSE, and BSE based on normalized A-share prefixes.
- A complete snapshot can deactivate provider-managed rows missing upstream.
- Empty, incomplete, schema-degraded, or provider-failed snapshots preserve the
  last good active universe and manual rows.
- Screening evaluates every in-scope stored active instrument. The API only
  bounds the final returned items/shortlist.
- Corporate-action sources are AkShare's Eastmoney dividend/bonus report-period
  dataset and CNInfo rights-allotment symbol dataset. Provider latency and
  reporting gaps remain visible in diagnostics.
- Only persisted eligible rows produce `market_daily_event:*` citations. Live,
  mock, static, unavailable, and provider-error rows are not citable.

## Safety and non-goals

- No natural-language rule generation in this release.
- No broker integration, order intent, buy/sell/hold instruction, target price,
  position sizing, portfolio weight, or automated trading.
- No InStock MySQL/Tornado runtime, proxy/cookie crawler, or hidden provider
  credential workflow is imported.
- AI explanations are rejected when they mention an unknown citation or an
  unknown backticked candidate symbol.

## Focused validation

```bash
pytest -q tests/providers/test_cn_market_providers.py tests/services/test_instrument_universe.py tests/services/test_stock_selection.py tests/services/test_stock_discovery.py tests/services/test_corporate_actions.py tests/services/test_market_daily_evidence.py
npm run test:web -- apps/web/components/stock-discovery-panel.test.tsx apps/web/components/market-daily-evidence-panel.test.tsx
```
