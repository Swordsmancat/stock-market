# Complete ingestion diagnostics backlog

## Goal

Complete the next high-priority ingestion diagnostics backlog so ingestion writes, returned payloads, TaskRun result payloads, and TaskRun detail UI diagnostics are consistent, observable, and covered by focused tests.

## Background

The previous Trellis work archived the design-only tasks for ingestion single-fetch and TaskRun quality diagnostics. Those designs established that session-backed ingestion currently fetches provider data twice and that the worker strips `quality_diagnostics` before completing the TaskRun. This task turns those designs into an implementation wave while preserving existing API behavior, retry behavior, and report lineage.

## Requirements

- Implement ingestion single-fetch first so returned snapshots, database writes, `bar_count`, and `quality_diagnostics` share one provider result.
- Persist ingestion `quality_diagnostics` in `TaskRun.result_json` after the ingestion data source is consistent.
- Display TaskRun quality diagnostics in the TaskRun detail UI with defensive parsing and localized user-visible text.
- Add additional high-value frontend API proxy or client interaction tests without changing backend contracts.
- Use child tasks for independently verifiable workstreams.
- Use subagents only where file ownership is non-overlapping or the work is read-only planning/review.
- Keep all subagents from committing or pushing; the main agent owns final verification, commits, and push requests.
- Preserve existing TaskRun retry behavior, report lineage, API wrapper shapes, and ingestion response compatibility.

## Acceptance Criteria

- [x] `ingest_market_snapshot(...)` fetches provider instruments and bars once per ingestion call and writes the same serialized snapshot that it returns and diagnoses.
- [x] Session-backed and no-session ingestion paths compute `bar_count` from the same snapshot shape.
- [x] Successful ingestion worker TaskRuns persist `result_json.quality_diagnostics` without changing TaskRun success/failure semantics.
- [x] TaskRun retry and report lineage behavior remain compatible with existing service tests.
- [x] TaskRun detail UI renders a dedicated quality diagnostics section for missing, OK, WARN, and FAIL diagnostics while keeping raw JSON fallback visible.
- [x] At least one additional high-value API proxy or client interaction path is covered by focused frontend tests.
- [x] Backend and frontend validation commands documented in `implement.md` pass before commit.
- [x] Final handoff lists completed child tasks, remaining deferred items, and tests run.

## Out of Scope

- Adding a new database schema for ingestion batches or quality diagnostics.
- Replacing public ingestion snapshot serialization with a raw internal provider object model.
- Changing TaskRun retry lineage or report lineage contracts.
- Treating data-quality `WARN` or `FAIL` as worker execution failure by default.
- Broad UI redesign outside the TaskRun detail diagnostics section and selected test coverage.

## Child Tasks

- `07-02-implement-ingestion-single-fetch`
- `07-02-persist-taskrun-quality-diagnostics`
- `07-02-display-taskrun-quality-diagnostics`
- `07-02-expand-proxy-client-interaction-tests`

## Notes

- The archived design sources are:
  - `.trellis/tasks/archive/2026-07/07-02-design-ingestion-single-fetch/design.md`
  - `.trellis/tasks/archive/2026-07/07-02-design-taskrun-quality-diagnostics/design.md`
- This is a complex parent task and requires `design.md`, `implement.md`, and curated child context before `task.py start`.
