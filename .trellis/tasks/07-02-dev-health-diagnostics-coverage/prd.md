# Add dev health diagnostics coverage

## Goal

Add non-mutating diagnostics to the scheduled/manual dev-health workflow so provider readiness and
TaskRun reliability checks run regularly without writing market data or requiring live provider
network access.

## Requirements

- Run mock provider readiness in `.github/workflows/dev-health.yml`.
- Run TaskRun health diagnostics in `.github/workflows/dev-health.yml`.
- Include existing provider readiness and TaskRun health tests in the workflow's focused health test step.
- Add a lightweight workflow regression test that guards the diagnostic commands and test entries.
- Avoid real-network provider checks, database mutations, or broad CI workflow changes in this slice.

## Acceptance Criteria

- [x] Dev-health workflow runs mock provider readiness.
- [x] Dev-health workflow runs TaskRun health diagnostics.
- [x] Focused health tests include provider readiness and TaskRun health tests.
- [x] Workflow regression coverage verifies these entries remain configured.
- [x] Focused script/workflow tests pass.
- [x] Task is committed, pushed, archived, and the next backlog item is inspected.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
