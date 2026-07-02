# Enhance report data lineage

## Goal

Strengthen report-level data lineage without introducing a database migration. Reuse the existing
`GeneratedReport.source_summary` JSON field and `GeneratedReport.task_run_id` column so generated
daily reports expose the price source, requested provider, citations, and task-run linkage across
store, detail, latest, history, and worker-generated payloads.

## Requirements

- Preserve the existing `source_summary.source` key and current API response shapes.
- Add compatible lineage fields to generated report source summaries:
  - `price_source`
  - `provider`
  - `requested_provider`
  - `task_run_id`
  - `citations`
- Pass the requested provider through report API and analysis service report generation paths.
- Ensure watchlist report refreshes associate each generated report with the watchlist task run.
- Expose `task_run_id` consistently from latest and history report payloads.
- Avoid schema migrations and row-level market data lineage changes in this slice.

## Acceptance Criteria

- [x] Daily report generation stores enriched `source_summary` JSON while preserving `source`.
- [x] Report list/detail/latest/history payloads include task-run lineage where available.
- [x] Stock and watchlist report worker tasks propagate provider and task-run lineage.
- [x] Focused API, worker, task-run, and migration tests pass.
- [x] No database migration is required for this change.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
