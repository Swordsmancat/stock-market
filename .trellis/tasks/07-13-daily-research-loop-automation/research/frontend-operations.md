# Daily research loop operations and frontend reuse

## Scope

Read-only audit of the current A-share evidence coverage, shortlist publication,
outcome evaluation, Celery/TaskRun, and AI Research frontend paths. The code
knowledge graph did not index this repository, so discovery fell back to
focused source, test, and task-document inspection as allowed by `AGENTS.md`.

## Recommendation

Do not add a new automation page, dashboard card, or AI Research panel for this
child task.

- `/ai-research` already owns the user workflow: the daily shortlist appears
  first, outcome tracking appears second, and evidence coverage/backfill remains
  secondary preparation tooling (`apps/web/app/[locale]/ai-research/page.tsx:137-220`).
- `/task-runs` already owns generic operational history, status filtering,
  detail, raw input/result lineage, failure text, and retry
  (`apps/web/app/[locale]/task-runs/page.tsx:39-55,98-199` and
  `apps/web/app/[locale]/task-runs/[taskRunId]/page.tsx:575-704`).
- `AshareEvidenceCoveragePanel` already owns evidence thresholds, exchange and
  source distribution, active backfill polling, resume/retry/cancel, and a link
  to the backfill TaskRun
  (`apps/web/components/ashare-evidence-coverage-panel.tsx:89-158,181-309,314-365`).
- Manual publication and manual outcome evaluation already exist in the two AI
  Research panels. The scheduled worker should call the same services directly,
  not introduce a second browser mutation contract.

If reverse lineage must be visible from the research surface, add only an
optional TaskRun link to the existing shortlist/outcome panels. That is a small
extension of those panels, not a new operational surface. Do not put daily-loop
status into `AshareEvidenceCoveragePanel`: its latest-run model and actions are
specifically a `ResearchEvidenceBackfill`, while publication/evaluation is a
separate orchestration responsibility.

## Existing coverage is not a trusted watermark

The coverage service preserves the required thresholds:

- daily bars: 95%;
- technical indicators: 90%;
- fundamentals: 80%.

They are defined in
`packages/services/research_evidence_backfill.py:35-59` and must not be lowered.
The response already exposes overall status, `as_of`, active/exchange counts,
per-dimension counts/ratios/thresholds, source distribution, latest backfill,
and safety flags (`packages/services/research_evidence_backfill.py:489-538`).

However, `status=ok` cannot be treated as a completed-day publication
watermark:

- `as_of` defaults to server `date.today()`
  (`packages/services/research_evidence_backfill.py:320-340`).
- The public coverage route exposes only `market` and `provider`, not a trusted
  cutoff (`apps/api/routers/stock_selection.py:54-67`).
- A stock is daily-bar ready with at least 35 rows in 18 months and a latest bar
  no older than ten days; it need not have a bar on the requested `as_of`
  (`packages/services/research_evidence_backfill.py:361-402`).
- Coverage does not apply the per-row completed-day ingestion rule used by the
  outcome ledger.
- Technical indicators may also be up to ten days old, while fundamentals are
  simply the latest complete snapshot in the 18-month horizon
  (`packages/services/research_evidence_backfill.py:413-487`).

The automation child therefore needs an internal, local-database-only watermark
resolver. For one candidate decision date it should expose:

- `status`: `ready`, `not_ready`, or `no_data`;
- `candidate_date` and nullable `verified_completed_through`;
- `market`, `asset_type`, timezone, and evaluation timestamp;
- active-universe denominator and exact-date completed daily-bar count/ratio;
- technical and fundamental ready counts/ratios using the unchanged 95/90/80
  thresholds and the existing exchange-presence gate;
- structured diagnostic codes for failed dimensions;
- confirmation that no provider/fallback/network path was used.

A daily bar may contribute to the exact-date watermark only when its
`ingested_at`, interpreted in Asia/Shanghai, is at or after 16:00 on its trade
date or falls on a later local date. Current-day verification is forbidden
before 16:00 and future dates are always forbidden. This matches the outcome
cutoff contract in
`packages/services/research_shortlist_outcomes.py:260-282` and its completed-bar
filter, rather than the broad coverage freshness rule.

The existing coverage payload remains useful supporting evidence and should be
captured in compact form in the TaskRun result. It is not itself the watermark.

## Shortlist and outcome service implications

### Explicit decision date

`generate_research_shortlist` currently derives the decision date from the
maximum `DailyBar.trade_date` held by any active in-scope stock
(`packages/services/research_shortlists.py:114-160,926-940`). A single partial
new-date row can therefore move that date before the full universe is ready.
The later coverage check is broad freshness coverage, and exact-date alignment
is enforced only candidate by candidate
(`packages/services/research_shortlists.py:173-260`).

The worker must pass its verified date into the generation service through an
internal-only argument. The browser request model must not be allowed to assert
a trusted watermark. Recomputing `max(trade_date)` after the gate would create a
time-of-check/time-of-use race.

The generation key already includes the decision date, normalized criteria,
rule/scoring versions, and shortlist limit, and duplicate generation reuses the
persisted run before repeating selection or explanation
(`packages/services/research_shortlists.py:145-175,425-451`). Preserve that
idempotency for scheduled and retry execution.

### Outcome maturation

The outcome evaluator already accepts both internal
`verified_completed_through` and `evaluation_task_run_id`
(`packages/services/research_shortlist_outcomes.py:91-145`). The public API does
not expose the trusted watermark, which is correct.

The orchestrator should enumerate every committed cohort that can still mature
a candidate horizon or pending benchmark, not only the newly published cohort,
then call the existing per-run evaluator with:

- `as_of=verified_completed_through`;
- `verified_completed_through=verified_completed_through`;
- `evaluation_task_run_id=current_task_run.id`.

The service remains local-DB-only and retains its candidate/horizon concurrency
guards. A bounded query should exclude cohorts whose three horizons and
benchmark observations are already terminal.

## Lineage gaps and proposed contract

The generic TaskRun record already serializes:

- `id`, `task_name`, `status`;
- start/finish/create time and duration;
- `input_json`, `result_json`, `error_message`;
- Celery ID and heartbeat
  (`packages/services/task_runs.py:27-46`).

It also supports bounded progress/heartbeat, enqueue, recent/latest/detail, and
retry (`packages/services/task_runs.py:76-103,133-239` and
`apps/api/routers/task_runs.py:15-45`). A new dispatcher registration is enough
for the existing failed-run retry button and proxy to work
(`apps/web/components/task-run-actions.tsx:14-44`). Celery Beat already runs in
Asia/Shanghai and has weekday A-share evidence schedules to precede this loop
(`apps/worker/celery_app.py:13-94`). The backfill worker/scheduler demonstrates
the direct-schedule plus pre-created retry TaskRun pattern
(`apps/worker/tasks/ingestion.py:520-619`).

Use a stable task name such as `research.run_daily_research_loop` and keep
TaskRun status in the existing operational vocabulary:

- `running`: worker owns the run and updates heartbeat/progress;
- `succeeded`: the orchestration completed, including an expected
  `not_ready`/`no_new_decision_date` domain result;
- `failed`: unexpected database/service/runtime failure, eligible for generic
  retry.

Recommended `input_json` fields:

- `market=CN`, `asset_type=stock`, `profile_id=balanced_research`;
- shortlist limit, locale, and `use_llm` policy;
- trigger (`scheduled`, `manual`, or retry); generic retry already adds
  `retry_of`.

Recommended stable `result_json` fields:

- top-level `status`, `research_signal_only=true`, and structured diagnostics;
- `watermark` with the fields above and compact coverage threshold evidence;
- `publication`: `status` (`created`, `reused`, `not_ready`, or `skipped`),
  `shortlist_run_id`, `generation_key`, `decision_date`, candidate count, and
  optional original publication TaskRun ID;
- `outcomes`: `evaluation_as_of`, considered/evaluated/reused run counts,
  candidate/horizon evaluated/pending/blocked totals, benchmark sample totals,
  and affected shortlist run IDs;
- final progress phase and timestamps.

TaskRun provides forward lineage into domain runs, but reverse lineage is
currently incomplete:

- `ResearchShortlistRun` has no TaskRun foreign key
  (`packages/domain/models.py:689-768`), and shortlist serialization exposes no
  generation TaskRun ID (`packages/services/research_shortlists.py:805-844`).
- `ResearchCandidateOutcome` already stores nullable
  `evaluation_task_run_id` (`packages/domain/models.py:996-1013`), but the public
  serializer omits it
  (`packages/services/research_shortlist_outcomes.py:1080-1109`).

To satisfy the parent requirement to expose TaskRun lineage:

1. Add nullable `generation_task_run_id` to `ResearchShortlistRun` and set it
   only when the run is first published. A retry that reuses a run must not
   overwrite the original publisher.
2. Expose `generation_task_run_id` in shortlist detail/latest responses.
3. Expose `evaluation_task_run_id` on terminal horizon responses. Pending
   derived horizons remain null.
4. Always record reused shortlist/outcome IDs in the current TaskRun result, so
   every retry remains auditable even though immutable domain rows retain their
   original creator.

Optional existing-panel TaskRun links may consume these fields. They are not a
reason to build another panel.

## Acceptance test matrix

### Watermark service

- No active in-scope stocks or no local bars -> `no_data`; no publication or
  outcome writes.
- A newer date held by only one stock cannot become the watermark.
- Exact-date daily-bar coverage immediately below 95% fails; exactly 95%
  passes. Technical 90% and fundamental 80% boundaries receive the same tests.
- Every required dimension retains nonzero SSE, SZSE, and BSE presence.
- Same-day pre-16:00 ingestion is excluded; same-day post-16:00 and later-date
  backfill ingestion are eligible. Naive SQLite timestamps follow the existing
  UTC normalization contract.
- Current Shanghai date is rejected before 16:00; future dates are rejected.
- Future bars/indicators/fundamentals do not leak into the cutoff.
- No provider, fallback payload service, HTTP client, or network adapter is
  called; query count is bounded with universe size.
- Returned diagnostics are structured codes and the 95/90/80 thresholds are
  unchanged.

### Generation and outcome orchestration

- Not-ready watermark finishes one observable TaskRun with a domain
  `not_ready` result and performs no domain mutation.
- Ready watermark passes the exact verified date into publication; generation
  cannot drift to a newer partial `DailyBar` date inserted between gate and
  publication.
- First run publishes one shortlist and records the generation TaskRun FK;
  duplicate, concurrent, scheduled, and retried executions reuse the same
  generation key/run without overwriting original lineage.
- Outcome maturation evaluates at least two prior cohorts through the same
  verified cutoff, materializes only ready horizons, and leaves not-ready
  horizons pending/null.
- Outcome rows created by the worker store and serialize
  `evaluation_task_run_id`; pre-existing terminal rows remain unchanged and are
  reported as reused in the current TaskRun result.
- Missing CSI 300 data preserves candidate absolute results and reports null
  relative metrics exactly as the outcome contract requires.
- A worker exception marks the TaskRun failed; retry dispatch carries
  `retry_of`, succeeds idempotently, and does not duplicate shortlist or
  outcomes.
- Progress phases update heartbeat during watermark, publication, outcome
  maturation, and completion; stale-run expiry still works.
- Scheduled execution and manual service invocation produce equivalent domain
  state and retain `research_signal_only=true`.

### Celery, API, and persistence

- Task dispatch registry recognizes the new task and forwards all stable input
  fields plus a pre-created TaskRun ID.
- Direct Celery Beat execution creates its own TaskRun; generic retry reuses the
  TaskRun created by `enqueue_task_run`.
- Beat schedule test asserts the new weekday task, Asia/Shanghai timezone,
  configured hour/minute, and stable kwargs. The watermark gate remains the
  authority even though the schedule runs after the existing 18:30 evidence
  refresh.
- Migration upgrade/downgrade covers the nullable shortlist TaskRun FK, index,
  and deletion behavior without touching immutable shortlist data.
- Latest/detail shortlist and outcome API tests assert nullable lineage fields;
  public request models reject caller-supplied trusted watermark and TaskRun
  lineage.
- TaskRun recent/latest/detail and retry API tests cover the new task name,
  structured result, failed retry, heartbeat, and stale expiry.

### Frontend reuse

- Existing Task Runs list renders the new task name/status and links to detail;
  a failed run exposes the existing Retry command.
- Task Run detail renders watermark, publication, and outcome lineage in the
  raw structured result without requiring a task-specific page.
- AI Research still renders shortlist, outcome, desk, coverage, and discovery
  in the existing order; automation failure cannot make the research workflow
  unavailable.
- Coverage `status=ok` is never relabeled in UI as a completed-day watermark.
- If optional lineage links are added, English/Chinese tests cover present and
  null lineage, correct `/task-runs/{id}` hrefs, and no backend free-form text
  leakage.
- Existing responsive/accessibility tests for shortlist, outcome, coverage,
  Task Runs, proxies, and both locale catalogs remain green. No scheduler setup
  controls are added to AI Research.

### Operational acceptance

- In the isolated acceptance stack, one verified completed A-share date creates
  one TaskRun, one idempotent shortlist, and all newly mature outcomes; a second
  execution reports reuse with unchanged domain row counts.
- TaskRun IDs can be followed to shortlist/outcome lineage and domain run IDs
  can be followed back to their original TaskRuns.
- A partial/intraday date remains `not_ready` and never becomes a published
  decision date.
- Normal ports 3000/8000 remain compatible, and no result/API/UI output adds
  trading instructions, portfolio actions, or automated execution.
