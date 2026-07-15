# Five-day personal research acceptance design

## Boundary

This is an operations-and-evidence task over the existing personal workflow.
The monitor reads production-local state and makes at most one explicitly
bounded assistant request per sampled trading date. It does not become another
scheduler for domain work and does not modify shortlist, outcome, backfill,
watchlist, portfolio, or order state.

The normal stack remains authoritative:

- Celery Beat schedules `research.run_daily_research_loop` on weekdays at
  21:30 Asia/Shanghai.
- The loop owns watermark, due-outcome maturation, and immutable publication.
- PostgreSQL owns TaskRun and shortlist identity.
- The existing 95/90/80 readiness thresholds remain unchanged.
- The assistant may use the configured model once, but deterministic ranking
  and shortlist membership remain independent of model output.

## Observation state machine

The durable source of truth is the set of exclusive
`artifacts/reservations/YYYY-MM-DD.json` markers. `artifacts/progress.json` is a
rebuildable projection; conversation history and automation wake count are
never used as the counter.

1. `monitoring`: run health and read-only evidence checks.
2. `pending`: a scheduled loop is still active or a post-baseline terminal run
   has not yet been consumed. A later wake queries bounded TaskRun history
   oldest-first rather than jumping directly to the newest watermark.
3. `skipped`: no new trusted watermark exists. Record at most one no-progress
   result for the Shanghai weekday window, make no assistant call, and keep
   monitoring.
4. `reserved`: atomically create the date marker with operating-system
   exclusive-create semantics. It records the trusted watermark, TaskRun ID,
   reservation time, and rank-one precondition state. It is the sole
   at-most-once guard; the day artifact and progress ledger are projections.
5. `observed`: store bounded assistant/citation metadata and the daily result.
   A timeout or provider error moves the date to `observed`, not a retry state.
6. `finalizing`: enter immediately after the fifth marker or a blocked-stop
   limit. No path in this state may call the assistant.
7. `complete` or `blocked`: write the final report and attempt delivery. The
   automation is disabled in a finalization `finally` path even if validation,
   commit, or push fails.

Reservation uses `CreateNew` / `O_EXCL`, never a check-then-write sequence. If
execution stops after `reserved` but before response capture, a later wake
records `assistant_outcome=unknown_after_reserved` and does not call again.
This favors a truthful missing result over an accidental duplicate paid call.

## Date sampling

A date is sampled when all of the following can be established:

- it is newer than `baseline.verified_completed_through`;
- no reservation marker exists for it;
- a terminal scheduled daily-loop TaskRun exposes the same trusted
  `watermark.verified_completed_through` value.

Shortlist publication and rank-one availability are assertions after sampling,
not eligibility filters. If either is missing, the assistant is not attempted
and the date is a failed observation. Holidays, weekends, active work,
deferred results without a new trusted watermark, repeated watermarks, and
pre-close current-day rows are not sampled.

Each wake queries a bounded 31-day scheduled TaskRun window and selects at most
one oldest unreserved trusted watermark. This recovers a loop that completed
after an earlier same-night check without reconstructing pre-baseline history.

## Evidence collection

Strictly read-only probes:

- `GET /health`, `GET /health/runtime`, and Web HTTP status;
- PostgreSQL and Redis connectivity;
- Worker ping and Beat process/schedule presence;
- `BEGIN READ ONLY` SQL for `research.run_daily_research_loop` TaskRuns;
- `GET /research-shortlists/latest`, shortlist detail/outcomes, and tracking.

The generic `GET /task-runs/*` API is not used because it invokes stale-run
expiration and can write to the database. The monitor also never invokes
shortlist generation, outcome evaluation, retry, or any backfill endpoint.

For a sampled date with a published rank-one candidate, the single assistant
request uses the fixed semantic intent `support_risk_invalidation_v1`. Literal
question and answer text are absent from artifacts. The recorded response
subset is limited to HTTP/result status, elapsed time, `used_llm`, safe model
name, fallback/error code, citation count/IDs, unknown citation IDs, diagnostic
codes, and safety flags.

## Artifact contracts

`artifacts/reservations/YYYY-MM-DD.json` is created atomically and contains:

- schema version, trusted watermark, scheduled TaskRun ID, and reservation
  time;
- shortlist/rank-one precondition state and assistant-call eligibility;
- no prompt, answer, credential, or provider payload.

`artifacts/progress.json` contains a rebuildable projection:

- schema version, task status, start/baseline timestamps;
- baseline trusted watermark and required count (`5`);
- ordered unique observed dates and per-date artifact paths;
- last check result, automation ID, hard deadline, no-progress weekday-window
  counter, finalization state, and completion time.

`artifacts/preflight.json` and `artifacts/days/YYYY-MM-DD.json` contain only
sanitized values. Day files use these top-level sections:

- `observation`: watermark, reservation/check timestamps, classification;
- `runtime`: component status and non-secret timing;
- `daily_loop`: TaskRun ID/status/scheduled-vs-start timing/result state;
- `shortlist`: run ID, generation-key fingerprint, coverage/gates, item count,
  and nullable rank-one symbol;
- `assistant`: at-most-once state and bounded response metadata;
- `outcomes`: cohort counts/statuses and duplicate detection;
- `assertions`: named pass/degraded/fail results;
- `redaction`: explicit confirmation that prohibited fields are absent.

Artifacts never contain environment dumps, database URLs, process command
lines, raw SQL rows, upstream payloads, prompt/answer text, or secrets.

## Result classification

- `pass`: runtime and loop are healthy, all coverage gates pass, shortlist is
  immutable, and the live assistant used the configured model with valid
  citations.
- `degraded`: the workflow remains usable but the model fell back, one
  non-critical source is unavailable, loop timing is late, or expected outcome
  horizons remain pending.
- `fail`: a sampled watermark lacks publication/rank one, a required
  service/loop assertion fails, a gate fails, the shortlist mutates/duplicates,
  citations are absent or invalid, or a safety boundary is violated.

The five-date completion condition is independent of these classifications.
The final report aggregates them instead of optimizing the sample. Monitoring
stops blocked at `2026-08-05T23:59:59+08:00` or after seven distinct weekday
evening windows without a new trusted watermark, whichever comes first.

## Timing, recovery, and finalization

The heartbeat runs at 22:15, 22:45, 23:15, and 23:45 on weekdays. Repeated
same-night wakes are read-only after a marker exists and provide bounded
rechecks for a late-running loop. A no-progress counter increments at most once
per Shanghai weekday, not once per wake, and resets after a reservation.

Transient failures are recorded and allowed to recur naturally on the next
trading date. No same-day assistant retry is permitted. A product/code fix is
considered only after the same reproducible blocker appears on at least two
sampled dates, unless a security, data-corruption, or service-availability
defect requires immediate containment. Any fix follows Trellis specs, tests,
commit, and push; thresholds and evidence rules are never weakened.

Finalization first persists `finalizing`, permanently closing the paid branch.
Report generation, validation, commit, and push then run best-effort;
automation disablement is a `finally` action for complete and blocked outcomes.
Delivery failure is recorded and surfaced, never retried by a paid monitor
wake. Rollback is simply disabling the automation because the monitor creates
no domain rows.
