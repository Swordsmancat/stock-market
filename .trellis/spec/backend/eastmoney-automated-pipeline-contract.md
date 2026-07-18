# Eastmoney Automated Collection Pipeline Contract

## Scope

The personal research installation runs four independent Eastmoney public-data
pipelines through the existing Celery Beat, Worker, PostgreSQL, and `TaskRun`
boundaries. The implementation is additive and does not authorize Eastmoney
login, browser-state access, account scraping, trading, or full-market
high-frequency crawling.

Implementation anchors:

- `packages/services/eastmoney_automation.py`
- `apps/worker/tasks/ingestion.py`
- `apps/worker/celery_app.py`
- `packages/services/crawler_monitor.py`
- `packages/providers/eastmoney_industry_rankings.py`
- `packages/services/fundamentals.py`

## Stable Pipelines

| Pipeline | Celery task | Default cadence |
| --- | --- | --- |
| Economic calendar | `ingestion.refresh_eastmoney_economic_calendar` | Daily 05:30 Shanghai |
| Industry ranking history | `ingestion.refresh_eastmoney_industry_rankings` | Weekdays 16:30 Shanghai |
| Research-universe news | `ingestion.refresh_eastmoney_research_news` | Every 60 minutes |
| Research-universe fundamentals | `ingestion.refresh_eastmoney_research_fundamentals` | Weekdays 19:30 Shanghai |

`EASTMONEY_AUTOMATION_ENABLED=false` removes all four Beat entries without
disabling explicit/manual read or refresh paths. Batch size, pacing, transient
attempts, retry delay, and schedule fields remain environment-backed settings
in `packages/shared/config.py`.

## Data And Failure Contracts

- Calendar and industry batches validate the complete bounded provider result
  before committing. Failed batches preserve the last stored revision.
- News and fundamentals use the latest committed CN shortlist followed by the
  active CN watchlist, deduplicated and bounded to the configured personal
  research batch size.
- News writes normalized deduplicated articles and sentiment only. Fundamentals
  write one coherent report-date snapshot plus normalized company metadata.
  A less complete Eastmoney snapshot must not overwrite richer stored evidence.
- News result semantics distinguish provider availability from deduplication:
  `empty` means the provider returned no items, while `skipped` means items were
  returned but none produced a new stored article (for example, every item was
  already present). This distinction must survive batch counts and TaskRun
  monitoring so an idempotent refresh is not reported as missing source data.
- A fresh `running` TaskRun with the same stable task name blocks overlap before
  provider work. Every accepted run records bounded progress and a truthful
  succeeded, failed, or skipped terminal state.
- Only transient timeout, connection, or rate failures receive bounded retry.
  Schema, identity, validation, and row failures stop without partial writes or
  retry storms.
- TaskRun and monitor payloads may contain only stable selectors, counts,
  progress, safe provider/model names, and allowlisted diagnostic codes. They
  never contain Cookies, proxy URLs, credentials, upstream bodies, exception
  text, stack traces, or environment dumps.

## Eastmoney Public Host Fallback

Industry collection is direct-first and uses only public Eastmoney endpoints:

1. Canonical `push2` or `push2his` host without a proxy.
2. Public `push2delay` host without a proxy.
3. The same bounded host list through the manually configured proxy, if any.

Every response still passes the same level-one taxonomy and finite-row
validation. The fallback does not read browser state, attach a generated
Cookie, follow redirects, or bypass access controls.

## Observability

`GET /crawler-monitor` projects four stable IDs: `eastmoney_calendar`,
`eastmoney_industry`, `eastmoney_news`, and `eastmoney_fundamentals`. This is a
bounded database-only read. The frontend refreshes the projection but never
dispatches, retries, cancels, or expires a TaskRun.

Required tests cover provider host fallback, transactional services, bounded
research-universe selection, fundamentals precedence, worker lifecycle and
overlap, Beat enable/disable behavior, monitor projection, localization, and
frontend decoding.
