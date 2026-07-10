# A-share Resumable Evidence Backfill Design

## Boundaries

Follow the parent design in `../07-10-live-market-pipeline-hardening/design.md`, sections 3-9 and 12-13. This child owns backend persistence, provider outcome classification, orchestration, coverage, APIs, worker/dispatch, schedules, and backend specifications/tests.

## Persistence

- Add `ResearchEvidenceBackfill` as the durable orchestration/checkpoint record linked to an authoritative TaskRun.
- Add nullable `TaskRun.heartbeat_at`; stale expiration uses heartbeat with `started_at` fallback.
- Existing evidence tables remain source of truth. Run state stores only checkpoint, counts, retry sets, bounded diagnostics, and lineage.

## Data Flow

```text
FastAPI create/resume/retry
  -> overlap validation + TaskRun/backfill creation
  -> Celery backfill task
  -> deterministic phase batches
  -> existing daily-bar/fundamental/indicator persistence
  -> checkpoint + heartbeat + counters + retry sets
  -> coverage projection
```

## Contracts

- Task: `ingestion.backfill_a_share_research_evidence`.
- API: create/get/resume/retry-failed/cancel under `/ingestion/a-share-evidence-backfills`.
- Coverage: `GET /stock-selection/evidence-coverage`.
- Run phases: `daily_bars`, `fundamentals`, `technical_indicators`.
- Run kinds: `baseline`, `incremental`, `fundamental_shard`, `canary`, `retry_failed`.
- Provider: public endpoint initially accepts `CN` + `akshare` only; internal types remain provider-neutral.

## Rollback

Disable Beat entries to stop new work, cooperatively cancel active runs, and revert additive routes/tasks/model usage. Existing evidence is retained. The migration downgrade removes only the new run table and heartbeat column.
