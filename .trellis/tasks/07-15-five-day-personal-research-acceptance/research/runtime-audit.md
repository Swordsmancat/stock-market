# Runtime and daily-loop audit

Audit timestamp: 2026-07-15, Asia/Shanghai. The audit was read-only and made no
model, generation, outcome-evaluation, retry, or backfill request.

## Confirmed contracts

- TaskRun and Celery task name: `research.run_daily_research_loop`.
- Beat entry: `daily-a-share-research-loop`, weekdays at 21:30
  Asia/Shanghai, with CN stock / `balanced_research`, shortlist limit 10,
  Chinese locale, LLM enabled, outcome run limit 25, scheduled trigger.
- Loop phases: completed-bar watermark, bounded due-outcome maturation, then
  immutable shortlist publication.
- The generic TaskRun GET service can expire stale rows and therefore is not a
  strict read-only probe. Direct `BEGIN READ ONLY` SQL is required.

## Baseline findings

- Web, API, PostgreSQL, Redis, Worker, and Beat were online.
- Latest scheduled loop succeeded on 2026-07-14, but started around 21:59
  rather than 21:30. Timing drift is an acceptance observation.
- Latest shortlist decision date was 2026-07-13 with 10 candidates. Coverage
  exceeded 95/90/80, but explanation metadata reported `used_llm=false` and a
  deterministic fallback after an HTTP provider failure.
- Outcome tracking exposed the latest cohort only; 5/20/60-session results
  were pending. Only the five-session horizon can plausibly mature during this
  acceptance.
- A separate daily watchlist-report TaskRun failed with sanitized message
  `No row was found when one was required`. It is not evidence that the daily
  research loop failed, but concurrency and shared-runtime effects should be
  watched.

## Operational risks to observe

- Another daily report is scheduled at 21:30 and may contend with the research
  loop on the single local worker.
- A 20:30 fundamental shard can overlap the loop. The watermark/readiness gates
  safely defer publication but may make the loop late or deferred.
- A successful manual model connection test does not guarantee scheduled
  generation succeeds. A repeated decision date reuses immutable model
  metadata, so only a new generation key can demonstrate recovery.
