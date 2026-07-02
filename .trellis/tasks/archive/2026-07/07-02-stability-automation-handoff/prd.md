# Stability automation handoff commit

## Goal

Prepare a clean handoff commit for the completed stability automation work, including only the project artifacts produced by the Task 1-4 implementation and final verification flow.

## Requirements

- Include the stability automation implementation artifacts:
  - scheduled dev health workflow
  - provider readiness diagnostic CLI and tests
  - market data quality service and tests
  - TaskRun health diagnostic CLI and tests
  - local development runbook updates
  - execution plan document for the stability automation work
- Exclude local agent/tool metadata directories unless the user explicitly approves them for version control:
  - `.agents/`
  - `.claude/`
  - `.codex/`
  - `.cursor/`
  - `.trellis/` content unrelated to this task, except this task's own Trellis artifact if included by policy
  - `AGENTS.md`
- Do not create a git commit until the user approves the PRD and task activation.
- Do not push unless the user explicitly requests it.
- Preserve the existing successful validation state; do not make broad code changes during handoff.

## Acceptance Criteria

- [ ] The git status is reviewed before staging.
- [ ] Only approved stability automation files are staged.
- [ ] Local agent/tool metadata directories are not staged unless separately approved.
- [ ] The commit message accurately describes the stability automation handoff.
- [ ] No push is performed without explicit user request.
- [ ] The final response summarizes the commit result and any remaining untracked files.

## Notes

- This is a lightweight handoff task; PRD-only planning is sufficient.
- Prior final verification reported focused tests, health checks, adjacent backend regression, and frontend tests passing.
