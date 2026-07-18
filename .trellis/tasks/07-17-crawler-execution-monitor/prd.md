# Add crawler execution monitor

## Goal

Provide a compact, truthful execution monitor for the personal research system's real collection pipelines. The page should answer which crawler is active, healthy, overdue, stalled, failed, or never recorded, with enough TaskRun evidence to investigate without starting or retrying work.

## Background

- Production TaskRuns currently record market ingestion, A-share universe sync, incremental evidence backfill, fundamental shards, and watchlist official-disclosure ingestion.
- Multiple logical pipelines share a task name and must be separated using bounded `input_json` selectors.
- Running backfills expose heartbeat and `result_json.progress` fields that can support live progress display.
- The supplied reference image uses a compact wrapping status strip; the new page should retain that scanning pattern while adding traceable detail.

## Requirements

- Add localized `/crawler-monitor` pages and a desktop-only sidebar/breadcrumb entry. Keep mobile bottom navigation at five destinations.
- Monitor seven real pipelines: CN/US/HK market ingestion, A-share instrument universe, daily A-share evidence, A-share fundamental shards, and watchlist official disclosures.
- Derive status from stored TaskRuns only. Normal page GET requests must not dispatch, retry, expire, mutate, or contact external providers.
- Use bounded TaskRun reads and deterministic task-name/input selectors.
- Distinguish `running`, `healthy`, `overdue`, `stalled`, `failed`, and `not_recorded` with text/icons as well as color.
- Treat a running row with an old heartbeat as stalled without mutating it.
- Show latest start/finish, duration, heartbeat freshness, schedule/cadence, provider/scope, bounded progress, recent failures, and a link to the stored TaskRun when available.
- Include a compact system-status strip and a detailed responsive table/list below it.
- Refresh visible status every 30 seconds and provide an explicit icon refresh control. Refresh remains read-only.
- Keep error, empty, and partial states distinct. Do not expose raw input/result JSON, stack traces, secrets, cookies, proxies, or environment values.
- Preserve the normal 3000/8000 stack and all unrelated dirty files, including the completed but uncommitted investment-calendar work.

## Out Of Scope

- Starting, retrying, cancelling, scheduling, or editing crawler jobs.
- Provider connectivity tests or live web scraping from the monitor page.
- Treating report generation, research publication, or alert evaluation as crawler pipelines.
- Adding new Celery schedules or database tables.

## Acceptance Criteria

- [x] `/zh/crawler-monitor` and `/en/crawler-monitor` open from the desktop sidebar while mobile navigation remains unchanged.
- [x] The API returns exactly the curated pipeline definitions with database-derived latest status and bounded evidence.
- [x] Shared task names are separated correctly by market and `run_kind` input selectors.
- [x] Active progress and heartbeat age render without exposing raw JSON.
- [x] Failed, stalled, overdue, and never-recorded pipelines remain visually and semantically distinct.
- [x] Page loading and auto-refresh are read-only and never expire, retry, or dispatch TaskRuns.
- [x] Backend and frontend tests cover status classification, selector matching, sanitization, navigation, failure states, and refresh behavior.
- [x] Ruff, formatting, TypeScript, full relevant tests, Trellis Check, and responsive light/dark browser verification pass.
