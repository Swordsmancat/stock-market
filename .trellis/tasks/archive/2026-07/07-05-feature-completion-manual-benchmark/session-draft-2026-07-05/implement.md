# Feature Completion Audit, Manual, and Professional Benchmark Plan - Implementation Plan

## Execution Order

1. Confirm task scope and Trellis planning artifacts.
2. Load relevant frontend/backend/spec guidance before code changes.
3. Audit existing Trellis tasks for planned, completed, and remaining financial features.
4. Audit repository structure and visible feature entry points.
5. Inspect representative frontend routes/components and backend/data provider paths.
6. Classify each major feature area as complete, partial, missing, or blocked.
7. Decide whether remaining implementation is small enough for this task or should become child tasks.
8. If implementation is sufficient, update manuals/documentation with current capabilities and limitations.
9. Benchmark implemented capabilities against professional financial websites and terminals.
10. Produce a prioritized follow-up plan and create/link child Trellis tasks for broad improvements.
11. Run validation checks appropriate to any touched files.
12. Record audit evidence, validation results, and next-step recommendations.

## Audit Checklist

- [x] Review active Trellis tasks under `.trellis/tasks/` for financial-dashboard, phase2/phase3, intraday, market depth, indicators, AI research, data cache/session governance, and website entry tasks.
- [x] Review documentation files such as README, manual, guides, or docs directories.
- [x] Review frontend routes and navigation labels to confirm feature discoverability.
- [x] Review API routes, providers, services, and adapters for market data implementation evidence.
- [x] Review tests and validation scripts relevant to implemented financial features.
- [x] Capture evidence in a task-local audit document.

## Implementation Gate

Implementation may begin only when all of the following are true:

- This task has been activated with `task.py start`.
- Audit evidence identifies a specific, small, directly related change.
- The target files have been read immediately before editing.
- Existing unrelated worktree changes will not be overwritten.

## Validation Plan

- Run project-provided lint/typecheck/test/build commands when they are discoverable and reasonably scoped.
- For documentation-only changes, run no-op-safe validation by reading rendered Markdown structure and checking internal links when feasible.
- For frontend code changes, run the nearest typecheck/lint/build command available in package scripts.
- For backend/provider changes, run focused tests or import checks if available.

## Rollback Points

- After audit document creation: audit files can be reverted independently from source code.
- After documentation updates: docs can be reviewed without impacting runtime behavior.
- After any small implementation patch: run focused validation before continuing.

## Expected Outputs

- [x] `audit.md` with feature completion evidence and status classification.
- [x] `professional-benchmark-plan.md` with competitive comparison and prioritized improvements.
- [x] Updated manuals/documentation if implementation is sufficiently complete. Current manuals were already updated in `README.md`, `docs/manual/user-guide.md`, and `docs/runbooks/developer-maintenance.md`; this task added task-local audit and benchmark evidence.
- [x] Child Trellis tasks for broad improvements discovered during benchmarking.

## 2026-07-05 Integration Update

Recent implementation work confirmed the audit conclusion: the product has several usable MVP-level financial workflows, but it is not yet at full professional financial terminal parity. The latest completed slices should be treated as execution evidence for this parent audit task even when they live under an earlier Phase 2 / Phase 3 parent task and cannot be re-parented by the Trellis CLI.

### Completed follow-up slices

- `07-05-ai-research-retrieval-citations` completed a research-citation MVP for the AI market assistant:
  - Added a service-local research evidence layer for daily bars, stored indicators, fundamentals, news, and generated reports.
  - Added optional citation metadata (`source_type`, `as_of`, `provider`, `retrieved_at`, `excerpt`, `metadata`) while preserving the existing citation contract.
  - Added LLM inline-citation validation and deterministic fallback diagnostics for unknown citation IDs.
  - Updated the frontend assistant card to render citation links, compact metadata, excerpts, and diagnostic severity/code.
  - Validation recorded in that task: backend assistant/API focused tests passed, frontend assistant focused tests passed, full web suite passed, and documentation was updated.
- `07-05-market-data-cache-session-governance` completed the first market-data reliability slice for intraday minute payloads:
  - Added top-level additive `freshness` and `session` metadata to `ok`, `no_data`, and `degraded` intraday paths.
  - Preserved the existing `GET /market-data/{symbol}/intraday?date=YYYY-MM-DD&timeframe=1m` status contract (`ok`, `no_data`, `degraded`).
  - Encoded provider/session skip reasons for future dates, weekends, known US-like holidays, unsupported providers, and provider-empty sessions.
  - Validation recorded in that task: `python -m py_compile "packages/services/market_data.py"`; focused backend readiness/API/service tests passed with `51 passed`; targeted no-data metadata regressions passed with `3 passed`; edited-file IDE diagnostics reported no diagnostics; whitespace check passed with CRLF conversion warnings only.

### Current professional-benchmark conclusion

- Complete enough for current MVP usage: localized website entry, market overview, individual security pages, provider-backed daily bars, basic indicators, watchlists/portfolio/alerts/report surfaces, AI assistant fallback behavior, manual/developer documentation.
- Partial / still behind professional products: persistent intraday cache, full exchange calendars, chart workspace depth, market breadth/sector rotation history, production market depth / Level-2 verification, recommendation backtesting and signal evaluation, filings/transcripts/announcements/vector retrieval for AI research, and real-time watchlist monitoring.
- Blocked / provider-dependent: live yfinance minute smoke success in this environment, AkShare/Tushare production depth/fund-flow verification, and any credentialed or paid data-provider capabilities.

### Remaining Trellis execution map

- Keep executing the existing children of this parent task for broad professional gaps:
  - `07-05-professional-chart-workspace-enhancements`
  - `07-05-hot-sector-production-breadth-rotation-history`
  - `07-05-recommendation-backtesting-signal-evaluation`
- Treat the completed AI and market-data reliability tasks as cross-linked evidence rather than re-parented children, because Trellis prevents attaching a child task that already has an existing parent.
- If the next priority remains market-data reliability, create a new narrowly-scoped child task under this parent for persistent intraday cache/storage or deeper exchange-calendar governance instead of mixing it into this audit task.
