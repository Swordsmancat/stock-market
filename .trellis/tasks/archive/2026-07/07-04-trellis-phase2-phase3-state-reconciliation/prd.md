# Trellis Phase 2/3 State Reconciliation

## Goal

Reconcile Trellis task status, parent/child links, and archive state for Phase 2 / Phase 3 work so task metadata matches the evidence from code, tests, documentation, and commits.

## Requirements

- Build an evidence matrix for active and archived Phase 2 / Phase 3 tasks.
- Identify task drift such as implemented work still marked `planning`, completed work still `in_progress`, or archived tasks with active references.
- Propose and apply safe task metadata changes only when code/tests/docs evidence supports completion.
- Preserve open tasks for partial or missing features, especially AI assistant, real intraday data, real market depth, and hot-sector fund-flow provider work.
- Avoid changing product code in this task unless needed to correct task metadata automation.
- Record any archived tasks with associated commit hashes and validation evidence.

## Acceptance Criteria

- [x] Phase 2 / Phase 3 task tree has no obvious orphaned audit task or duplicated archived active task.
- [x] Implemented-and-verified tasks are archived or explicitly documented as still open with remaining gaps.
- [x] Missing/partial features remain active with actionable PRDs.
- [x] Parent task progress reflects child task status as accurately as Trellis supports.
- [x] Session journal records the reconciliation decisions and commit hashes.

## Completion Notes (2026-07-05)

- Archived completed children for intraday chart, Phase 2 hardening acceptance closure, website-entry feature gap plan, and performance-data-fix.
- Parent `07-04-07-04-phase2-phase3-financial-features-completion` now reflects `13/14 done` before archiving this reconciliation child.
- Remaining professional-terminal gaps are documented as follow-up work rather than hidden active MVP blockers.
- Top-level active tasks that are intentionally still open remain separate from this Phase 2/3 child tree: frontend UI polish and professional dashboard enhancement.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
