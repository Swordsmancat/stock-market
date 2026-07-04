# Feature Completion Audit Manual and Roadmap Implementation Plan

## Slice 1: Evidence Matrix

1. Consolidate subagent audit findings into a stable completion matrix.
2. Record status for every requested Phase 2 and Phase 3 feature.
3. Distinguish complete implementation from degraded-safe fallback contracts.
4. Identify missing or partial features that require follow-up Trellis tasks.

## Slice 2: Manual Updates

1. Add `docs/manual/user-guide.md` with user-facing feature status and usage notes.
2. Add `docs/runbooks/developer-maintenance.md` with endpoint catalog, degraded-safe provider contracts, validation commands, and provider capability notes.
3. Update `README.md` with a documentation index and current Phase 2 / Phase 3 feature-status summary.

## Slice 3: Professional Benchmark and Roadmap

1. Add a comparison section covering TradingView-style charting, Bloomberg/Koyfin-style research terminals, stock screeners, broker terminals, and CN retail terminal expectations.
2. Convert major gaps into prioritized improvement items.
3. Create Trellis tasks for large follow-ups that should not be hidden inside this audit task.

## Slice 4: Trellis Task Hygiene

1. Link the current audit task under the Phase 2 / Phase 3 parent task if the parent exists.
2. Create follow-up tasks for:
   - AI market assistant.
   - Real intraday minute-bar provider pipeline.
   - Real market-depth / large-order / fund-flow provider pipeline.
   - Real hot-sector fund-flow backend/provider support.
   - Trellis status reconciliation for completed-but-unarchived tasks.
3. Do not archive unrelated tasks in this slice unless the evidence matrix and current task explicitly justify it.

## Validation

- `npm run test:web` if README/docs-only changes do not affect runtime, this still acts as frontend regression coverage.
- `python -m pytest tests/api/test_market_depth_api.py tests/api/test_market_data_intraday_api.py tests/api/test_market_data_api.py` to recheck recently completed degraded-safe contracts.
- `git diff --check` to catch documentation whitespace issues.

Completed validation:

- `git diff --check`
- `npm run test:web`
- `python -m pytest tests/api/test_market_depth_api.py tests/api/test_market_data_intraday_api.py tests/api/test_market_data_api.py`

## Status

Completed. The task produced an evidence-based Phase 2 / Phase 3 completion matrix, added user and maintainer manuals, updated the README documentation index and feature-status table, and created Trellis follow-up tasks for large remaining gaps.

## Commit Policy

Commit and push task-related documentation, Trellis planning, and roadmap updates. Do not include unrelated `apps/web/app/api/recommendations/route.ts` line-ending noise.
