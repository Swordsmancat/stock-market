# Phase 2 and 3 Financial Features Completion Implementation Plan

## Global Checklist

1. Document the remaining Phase 2/3 audit outcome.
2. Fill child-task PRDs with testable acceptance criteria.
3. For each complex child task, add `design.md` and `implement.md` before implementation starts.
4. Start one child task at a time with `task.py start`.
5. Use readonly subagents for targeted research and review before large edits.
6. Implement a narrow slice.
7. Run focused tests for the slice.
8. Run broader tests when frontend or shared logic changes.
9. Commit and push passing slices.
10. Update the parent audit matrix as each slice closes.

## Initial Execution Slice

Start with `07-04-phase2-hardening-acceptance-closure` because it closes gaps in code that already exists and should produce a small, verifiable commit.

## Validation Commands

Use the relevant subset per slice:

```powershell
npm run test:web
python -m pytest tests/api/test_recommendations_api.py
python -m pytest tests/analytics/test_indicators.py tests/services/test_indicator_persistence_service.py tests/api/test_indicators_db_api.py
```

Run `ReadLints` on edited frontend files after substantive UI edits.

## Commit Policy

The user authorized automatic commit and push. Commit only files that belong to the completed slice and avoid unrelated working tree noise.
