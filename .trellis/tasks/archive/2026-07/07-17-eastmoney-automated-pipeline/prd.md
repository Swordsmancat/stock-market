# Build automated Eastmoney collection pipeline

## Goal

Turn the existing on-demand Eastmoney public-data adapters into a complete,
continuous, observable collection loop for a personal research installation.
The loop should keep the most useful Eastmoney evidence current without
requiring page visits or manual refreshes.

## Background

- Public Eastmoney adapters and transactional storage already exist for the
  economic calendar and level-one industry ranking history.
- Public Eastmoney news ingestion already persists normalized `NewsArticle`
  and sentiment rows for one exact A-share symbol.
- Public Eastmoney fundamentals/company reads are bounded and normalized but
  currently remain read-through/cache-only and do not provide a scheduled
  persistence path.
- Celery Beat, Worker, `TaskRun`, active watchlist entries, daily research
  shortlist candidates, and the read-only crawler monitor already exist.
- This is a personal research product. Complete means a complete operational
  loop over the useful data domains, not high-frequency crawling of the full
  Eastmoney site or every A-share symbol.

## Requirements

- Add four independently scheduled and observable Eastmoney pipelines:
  economic calendar, level-one industry history, research-universe news, and
  research-universe fundamentals/company metadata.
- Build the research universe deterministically from active A-share watchlist
  entries plus the latest persisted daily shortlist, deduplicated and bounded.
- Keep economic-calendar and industry-history refreshes transactional: validate
  the complete bounded provider response before committing and preserve prior
  data on provider failure.
- Add an explicit Eastmoney fundamentals persistence path that stores one
  coherent normalized report snapshot; never stitch fields across report dates
  or invent missing PE/company fields.
- Reuse the existing Eastmoney public-news persistence path with bounded symbol
  batches, per-request pacing, and deterministic deduplication.
- Record every scheduled execution as its own `TaskRun`, including safe input
  selectors, heartbeat/progress, counts, sanitized diagnostic codes, terminal
  status, and duration.
- Prevent overlapping executions of the same pipeline. A duplicate scheduled
  wake should record or return a bounded skip result rather than issuing a
  second provider batch.
- Apply bounded retry/backoff only to transient transport/rate failures. Schema,
  identity, and validation failures must stop the affected pipeline and preserve
  stored evidence.
- Keep direct public HTTPS requests as the primary path. The existing manually
  configured industry Cookie/proxy may remain an optional fallback; never read
  browser state, log credentials, or expose secret values through APIs or
  `TaskRun` payloads.
- Extend `/crawler-monitor` with the four Eastmoney pipeline definitions and
  localized status/scope/cadence labels. Page loads and refreshes remain
  database-only and non-mutating.
- Preserve existing manual refresh actions, existing AkShare/yfinance/Tushare
  fallbacks, the five-item mobile navigation, and the normal 3000/8000 stack.
- Keep schedules configurable through environment-backed settings with
  conservative defaults suitable for one local user.

## Default Schedule

- Economic calendar: daily before the morning research session, refreshing a
  bounded rolling window.
- Industry history: weekdays after the A-share close.
- Research-universe news: hourly, with a bounded symbol count and request delay.
- Research-universe fundamentals/company: weekdays after the market-data jobs,
  with a bounded symbol count and request delay.

## Out Of Scope

- Logging into an Eastmoney account or harvesting browser Cookies.
- Scraping authenticated/private account, portfolio, order, or trading data.
- Full-site crawling, full-A-share hourly news scans, or bypassing anti-bot and
  access controls.
- Automated trading, recommendations, order placement, or model calls.
- Replacing existing providers or deleting manual refresh controls.

## Acceptance Criteria

- [x] Four stable Celery task names and Beat schedules exist with conservative,
      configurable defaults and no overlap between identical pipeline runs.
- [x] Each pipeline creates a bounded, secret-safe `TaskRun`, reports progress,
      and reaches a truthful succeeded/failed/skipped terminal result.
- [x] Economic calendar and industry history update stored rows automatically
      and preserve previous rows on any incomplete provider batch.
- [x] News refreshes only the bounded active research universe and persists
      normalized, deduplicated articles/sentiment without raw upstream bodies.
- [x] Fundamentals/company refresh persists coherent report-date snapshots for
      the bounded research universe without fabricating unavailable values.
- [x] Transient failures use bounded backoff while schema/identity failures stop
      without retry storms or partial destructive writes.
- [x] The crawler monitor shows all Eastmoney pipelines and remains a read-only
      projection with distinct running/healthy/overdue/stalled/failed states.
- [x] Settings/API/monitor payloads expose only configured booleans and safe
      metadata; Cookies, proxies, credentials, upstream bodies, and stack traces
      never appear.
- [x] Focused provider/service/worker/API/frontend tests, full relevant suites,
      Ruff, TypeScript, Trellis Check, and live Docker acceptance pass.
