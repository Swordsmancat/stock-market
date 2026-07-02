# Audit remaining backlog checklist

## Goal

Produce a read-only remaining-backlog checklist based on current Trellis tasks, recently pushed implementation work, plans, docs, and repository state.

## Requirements

- Inspect current Trellis active and archived tasks.
- Inspect the current git status and recent commits.
- Review the active parallel backlog execution task state, including deferred lanes.
- Review relevant plan documents and implementation audit outputs to identify open work.
- Distinguish completed work from remaining work and deferred work.
- Prioritize remaining items into short-term, medium-term, and larger product/architecture work.
- Do not modify source code, task state, docs, git commits, or remote branches during this audit.
- Mark uncertain items as requiring confirmation instead of presenting them as implementation facts.

## Acceptance Criteria

- [ ] Current Trellis task list is summarized.
- [ ] Current git status and recent commits are summarized.
- [ ] Deferred items from the parallel execution plan are captured.
- [ ] Remaining backlog is listed as a clear prioritized checklist.
- [ ] Completed items are separated from open work.
- [ ] No files are modified and no commit/push is performed.

## Notes

- This is a lightweight read-only audit task; PRD-only planning is sufficient.
- The user asked to detect the remaining to-do checklist after Phase 1/2 parallel backlog execution work was committed and pushed.
