# Feature Completion Audit, Manual, and Professional Benchmark Plan

## Goal

Assess whether the existing financial dashboard / market analysis product has completed its planned functionality, continue implementation only when meaningful gaps remain, complete user-facing manuals when implementation is already sufficient, and benchmark the implemented product against professional financial websites to produce and execute a prioritized Trellis-backed improvement plan.

## Requirements

- Treat this as a task separate from the unavailable prior session `4d53d264-0019-48ab-bf4c-ecbf8bc20045`.
- Preserve existing worktree changes and do not revert unrelated modifications.
- First perform a read-only completion audit across current Trellis tasks, source code, documentation, and visible feature entry points.
- Determine whether the currently planned/claimed features are implemented, partially implemented, or missing.
- If remaining implementation work is small, complete it inside this task after the required Trellis planning gate.
- If remaining implementation work is broad or spans independent deliverables, create child Trellis tasks instead of mixing unrelated changes into this task.
- If planned features are already sufficiently implemented, prioritize completing manuals and usage documentation.
- Compare implemented capabilities with professional financial websites and terminals, including but not limited to TradingView, Yahoo Finance, Bloomberg-style quote pages, Eastmoney, Tonghuashun, and Futu/Moomoo-style market dashboards.
- Evaluate whether the product meets current functional expectations for market overview, individual security analysis, intraday / historical charts, technical indicators, sector / fund-flow views, AI research, data reliability, and navigation discoverability.
- Produce a concrete improvement plan with priority, scope, acceptance criteria, and Trellis execution mapping.

## Constraints

- Do not depend on the missing prior transcript file; reconstruct context from repository artifacts and existing Trellis tasks.
- Do not overwrite or normalize the many existing uncommitted changes unless they are directly required for this task.
- Do not start implementation until planning artifacts are reviewed and the Trellis task is activated.
- Keep audit conclusions evidence-based and cite the repository artifacts or runtime checks used to support each conclusion.
- Favor incremental, independently verifiable follow-up tasks over broad all-in-one implementation.

## Acceptance Criteria

- [x] Existing Trellis tasks and code paths relevant to financial features are audited and summarized.
- [x] Each major feature area is classified as complete, partial, missing, or blocked.
- [x] If incomplete features are found, the next implementation action is either completed here or split into child Trellis tasks with clear acceptance criteria.
- [x] If features are complete enough, user/developer manuals are updated or a concrete documentation patch is prepared.
- [x] Current implemented capabilities are benchmarked against professional financial websites.
- [x] Gaps and optimization opportunities are prioritized by user value, implementation risk, and dependency order.
- [x] A Trellis execution plan exists for follow-up improvements, including parent/child mapping when the scope is large.
- [x] Validation commands and manual review steps are documented before any implementation begins.

## Completion Notes

- Added task-local `audit.md` with feature-area status classification, implementation evidence, and validation evidence.
- Added task-local `professional-benchmark-plan.md` comparing the current product against TradingView/Yahoo Finance/Bloomberg-style/Eastmoney/Tonghuashun/Futu-style expectations.
- Executed three broad follow-up slices through Trellis tasks instead of folding them into one audit patch: hot-sector metadata, local chart workspace, and recommendation signal evaluation.
- Manuals and maintainer docs now describe current MVP capabilities, degraded-safe provider limits, research-only chart/recommendation semantics, and focused validation commands.
- Remaining professional-terminal parity work is explicitly mapped to follow-up Trellis tasks rather than marked complete.

## Notes

- This task is primarily an audit, documentation, and planning task. Implementation should remain scoped and evidence-driven.
- Large functional upgrades discovered during benchmarking should become child tasks rather than being folded into this audit task.
