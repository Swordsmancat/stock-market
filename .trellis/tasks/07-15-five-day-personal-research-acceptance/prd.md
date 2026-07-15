# Run five-day personal research acceptance

## Goal

Validate the existing single-user A-share research workflow against five
distinct, newly completed trading dates before deciding whether any further
product work is justified. The acceptance must measure the scheduled daily
loop, immutable shortlist, stored evidence, cited assistant response, and
outcome tracking as they operate in the user's normal local stack.

## Requirements

- Record a read-only preflight baseline before the first accepted date. The
  baseline decision date does not count toward the five-day sample.
- Observe five distinct trusted `verified_completed_through` values newer than
  the baseline, each tied to a terminal scheduled daily-loop TaskRun. Reserve
  the sample date before requiring successful publication so a coverage or
  no-candidate failure cannot be omitted from the sample. A weekday, calendar
  day, holiday, deferred loop without a new trusted watermark, or repeated
  watermark does not count by itself.
- Run the observation after the normal weekday 21:30 Asia/Shanghai daily loop,
  initially at 22:15. Do not change the production loop schedule during the
  acceptance.
- For every check, verify Web, API, PostgreSQL, Redis, Worker, and Beat health;
  inspect the exact `research.run_daily_research_loop` TaskRun through a
  read-only database transaction; and read the latest shortlist and outcome
  tracking surfaces.
- Preserve the existing publication gates: at least 95% daily-bar coverage,
  90% critical technical-indicator coverage, and 80% complete-fundamental
  coverage. A failed gate is evidence, never permission to lower a threshold.
- For each newly observed watermark, atomically create one exclusive
  date-named reservation marker before updating projections or making a live
  `POST /assistant/market` attempt. The marker is the authority: if it already
  exists, no process may call the assistant for that date. Make at most one
  attempt when a rank-one candidate exists; otherwise record
  `not_attempted_precondition` and count the date as failed. Never retry after
  a timeout, provider failure, process interruption, or fallback response.
- Validate that the assistant response is based on stored evidence, returns
  citations, and does not invent citation identifiers. Record status and
  bounded metadata only; never store the question, answer, prompt, key,
  authorization header, provider body, credential-bearing URL, or stack trace.
- Record each observed date once even when publication, coverage, candidate
  selection, or assistant use is degraded or failed. Do not extend the sample
  or silently replace a bad day with a later good day.
- Verify shortlist identity is immutable for the decision date and outcome
  tracking does not create duplicate cohorts. Pending 20/60-session outcomes
  are expected within this five-day window and are not acceptance failures.
- Keep the normal `3000`/`8000` services available. Do not trigger shortlist
  generation, outcome evaluation, TaskRun retry, backfill, watchlist mutation,
  portfolio mutation, order placement, or automated trading from the monitor.
- Do not alter the protected homepage or add product features. A code change is
  allowed only for a repeatedly reproduced blocker that prevents the personal
  workflow from being evaluated; it must have focused regression tests and be
  committed and pushed separately from evidence-only updates.
- Stop as blocked, write a bounded report, and disable the automation if five
  samples are not reserved within 21 natural days of the baseline or after
  seven distinct weekday observation windows produce no new trusted watermark.
  Completion and blocked finalization must both permanently close the paid-call
  branch before delivery checks begin.

## Acceptance Criteria

- [ ] A sanitized preflight artifact records the baseline decision date,
      runtime health, latest daily-loop state, coverage, LLM/fallback metadata,
      and outcome summary.
- [ ] Five sanitized day artifacts and five exclusive reservation markers
      exist for five unique trusted watermark dates newer than the baseline,
      with no duplicate assistant attempt; or a bounded blocked report explains
      which explicit stop limit was reached.
- [ ] Every day artifact records service health, daily-loop timing/status,
      95/90/80 gate results, shortlist identity, rank-one candidate identity,
      assistant call outcome/citation validation, and cohort tracking summary.
- [ ] Failures and degraded states are reported honestly without retries,
      threshold relaxation, automatic mutation, or sample replacement.
- [ ] A final report distinguishes product friction from data/provider/runtime
      incidents and recommends only the smallest evidence-backed next action.
- [ ] Any required code fix passes focused and relevant full checks, is
      committed, and is pushed without staging the user's unrelated changes.
- [ ] After the fifth reservation or a blocked stop, status changes to
      `finalizing` before any delivery work, the paid-call branch stays closed,
      and the automation is disabled even when validation, commit, or push
      fails. Successful delivery also completes the Trellis finish flow.

## Out of Scope

- Trading decisions, orders, broker integration, portfolio allocation, or
  watchlist changes.
- New providers, screening rules, prompts, dashboards, or first-class modules.
- Historical reconstruction before the baseline. Bounded terminal scheduled
  runs after the baseline may be consumed oldest-first when a late loop finishes
  after the first same-night check.
- Treating a deterministic fallback as equivalent to a successful paid-model
  response; it remains usable but is recorded as degraded.
