# Eastmoney Automated Pipeline Runbook

## What Runs

The local installation continuously stores four public Eastmoney evidence
domains: economic-calendar events, level-one industry history, research-symbol
news, and research-symbol fundamentals/company metadata. Celery Beat schedules
the work, one Worker executes it, PostgreSQL owns the durable result, and
`/zh/crawler-monitor` shows the latest safe status.

The research universe is intentionally small: the latest committed A-share
shortlist first, followed by active A-share watchlist symbols, deduplicated and
limited by `EASTMONEY_RESEARCH_BATCH_SIZE` (default 20).

## Configuration

| Environment setting | Default | Purpose |
| --- | --- | --- |
| `EASTMONEY_AUTOMATION_ENABLED` | `true` | Enable all four Beat schedules |
| `EASTMONEY_CALENDAR_CRON_HOUR/MINUTE` | `5` / `30` | Daily calendar refresh |
| `EASTMONEY_INDUSTRY_CRON_HOUR/MINUTE` | `16` / `30` | Weekday industry refresh |
| `EASTMONEY_NEWS_INTERVAL_MINUTES` | `60` | News refresh interval, minimum 15 |
| `EASTMONEY_FUNDAMENTALS_CRON_HOUR/MINUTE` | `19` / `30` | Weekday fundamentals refresh |
| `EASTMONEY_RESEARCH_BATCH_SIZE` | `20` | Maximum news/fundamental symbols |
| `EASTMONEY_REQUEST_DELAY_MS` | `1000` | Delay between symbol requests |
| `EASTMONEY_MAX_TRANSIENT_ATTEMPTS` | `2` | Bounded transient attempts |
| `EASTMONEY_RETRY_BASE_SECONDS` | `2.0` | Retry backoff base |

Schedules use `Asia/Shanghai`. A manually configured Eastmoney proxy or Cookie
remains optional for the existing industry adapter, but the application never
extracts browser state and never exposes either value in API or TaskRun data.

## Normal Checks

1. Open `http://127.0.0.1:3000/zh/crawler-monitor`.
2. Confirm the four Eastmoney rows are `healthy` or actively `running`.
3. Use `docker compose ps` to confirm API, Web, PostgreSQL, Redis, Worker, and
   Beat are running.
4. Use `docker compose logs --tail 100 worker beat` only for local diagnosis;
   never publish raw exception output or configuration values.

The monitor is read-only. Refreshing the page does not contact Eastmoney or
change TaskRun rows.

## Failure Handling

- `failed` with an industry request code: verify public network access. The
  adapter tries canonical public hosts, then `push2delay`, then a manually
  configured proxy if present.
- Schema or row rejection: do not retry repeatedly and do not lower validation.
  Preserve stored rows, inspect the provider contract, update fixtures/tests,
  then perform one bounded live run.
- News or fundamentals provider-wide failure: leave the batch failed, keep its
  TaskRun evidence, and wait for the next scheduled run after confirming public
  access. Do not expand the symbol limit as a recovery action.
- Stalled task: verify Worker/Redis health. Overlap protection prevents a second
  identical fresh run from issuing another provider batch.

To stop scheduled collection without deleting stored evidence, set
`EASTMONEY_AUTOMATION_ENABLED=false` and recreate Beat. Existing database-only
pages and explicit/manual refresh routes remain available.

## Replacing A Source

Keep provider adapters behind the service boundary. A replacement must return
the same normalized identities, dates, finite values, source provenance, and
retrieval timestamps; it must pass complete-batch validation before commit.
Never merge a different industry taxonomy into Eastmoney level-one history or
stitch financial fields from different report dates.
