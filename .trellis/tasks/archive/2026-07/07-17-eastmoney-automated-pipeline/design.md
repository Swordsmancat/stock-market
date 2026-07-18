# Eastmoney automated pipeline design

## Architecture

Add four small Celery tasks under the existing ingestion worker boundary. Each
task owns one `TaskRun` lifecycle and calls one service-level batch operation.
Celery Beat schedules the tasks independently so failures and freshness remain
isolated and observable.

The batch service layer reuses existing normalized providers and storage
services. It does not parse HTML in workers, call frontend routes, or introduce
a second scheduler/database. A shared bounded research-universe resolver reads
active A-share watchlist entries and the latest persisted shortlist.

## Pipeline Contracts

### Economic calendar

- Stable task: `ingestion.refresh_eastmoney_economic_calendar`.
- Refresh a bounded rolling window accepted by the existing 62-day provider
  contract.
- Reuse `refresh_economic_calendar`; commit only a fully validated result.

### Industry ranking history

- Stable task: `ingestion.refresh_eastmoney_industry_rankings`.
- Refresh the existing bounded 20-day Eastmoney level-one taxonomy.
- Reuse `refresh_industry_rankings`; direct request first, configured proxy and
  manually supplied Cookie only through the existing secret-safe boundary.

### Research-universe news

- Stable task: `ingestion.refresh_eastmoney_research_news`.
- Resolve a bounded union of active A-share watchlist symbols and latest daily
  shortlist symbols.
- Call the existing `ingest_akshare_news` compatibility path, which is backed by
  `eastmoney_public`, sequentially with a configurable delay.
- Count ingested/empty/skipped/provider-error symbols. Provider-wide repeated
  transport/rate failures terminate the batch with a safe diagnostic.

### Research-universe fundamentals/company

- Stable task: `ingestion.refresh_eastmoney_research_fundamentals`.
- Add a write-specific service around the existing normalized Eastmoney public
  provider. Persist exactly one coherent `FundamentalSnapshot` per symbol/report
  date and normalized company metadata only in an existing compatible storage
  location or a narrowly scoped additive model/migration if no compatible owner
  exists.
- Do not reuse the current read-through GET path for persistence because its
  contract explicitly forbids ORM writes.

## TaskRun And Concurrency

Each task accepts an optional `task_run_id` for existing dispatch compatibility.
Direct Beat execution starts its own row. Input JSON contains only stable fields
such as `provider=eastmoney_public`, `pipeline`, range/batch limits, and trigger.

Before provider work, query for another fresh `running` row with the same stable
task name. If present, stop before any provider call with a bounded overlap-skip
result. Running tasks update progress after each bounded page/symbol phase.
Errors stored in TaskRun use stable diagnostic codes or generic messages only.

## Retry And Rate Policy

Use sequential requests and configurable delays. Retry only sanitized transient
classes (timeout, connection, explicit rate status) with a small exponential
backoff and strict attempt limit. Do not retry schema, row, identity, response
size, redirect, media-type, or validation errors. No task retries indefinitely.

## Scheduling Defaults

- Calendar: daily early morning.
- Industry history: weekday after close.
- News: hourly, bounded to the personal research universe.
- Fundamentals/company: weekday evening, separated from existing A-share
  incremental and fundamental-shard jobs.

All schedules are environment-backed. Disabling the Eastmoney automation flag
removes these Beat entries without disabling manual refresh routes.

## Monitor Integration

Extend the curated monitor contract rather than exposing generic TaskRun rows.
Each new stable task name maps to a dedicated pipeline ID, cadence, freshness,
stall threshold, and localized labels. The endpoint continues to perform one
bounded read and never expires or changes rows.

## Compatibility And Rollback

- Existing provider adapters, manual POST refreshes, and GET projections remain
  compatible.
- New settings default conservatively and can disable the schedules as one
  rollback switch.
- New tasks are additive and can be removed from Beat without deleting stored
  evidence.
- Any required migration must be additive and SQLite/PostgreSQL compatible.
