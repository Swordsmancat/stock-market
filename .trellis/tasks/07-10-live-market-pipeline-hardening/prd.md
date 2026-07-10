# Live Full-Market Pipeline Acceptance and Production Hardening

## Goal

Prove that the newly integrated full A-share research workflow operates safely against real AkShare data, then close only the reliability and observability gaps found by that evidence. The outcome must distinguish provider limitations from product defects and must not silently turn missing or partial upstream data into successful research evidence.

## Background

- Commit `9a3848a` added failure-safe SSE/SZSE/BSE universe synchronization and cursor-based corporate-action ingestion.
- Commit `2e9ea74` added deterministic full-universe screening, named profiles, coverage counters, and citation-constrained AI explanation.
- Commit `d90e35a` exposed the workflow through `/ai-research` and `/evidence`.
- Automated validation passed before this task: 527 backend tests, 194 Web tests, and TypeScript checking.
- The local runtime uses PostgreSQL/TimescaleDB, Redis, FastAPI, Celery worker/beat, and Next.js. The default Docker database volume is persistent.
- `scripts/provider_readiness.py --provider akshare --market CN --real-network` already provides a non-mutating network smoke check. It does not prove database reconciliation, task dispatch, cursor continuation, full-universe screening, or browser behavior.
- The current universe job synchronizes instrument identity only. Daily-bar batch ingestion loops over requested symbols sequentially, while fundamentals and indicator calculation remain single-symbol operations without a resumable full-universe cursor job.
- The real-network provider is an external dependency. Empty responses, schema drift, throttling, timeouts, report-period gaps, and partial per-symbol failures are expected operational states and must remain visible.

## Requirements

### R1. Isolated, reproducible acceptance environment

- Run acceptance against an isolated PostgreSQL database named `stock_acceptance` and a dedicated Redis database/namespace.
- The existing local `stock` database must not receive acceptance writes.
- Record the exact application commit, dependency versions, migration head, provider, market, report period, timestamps, and commands used.
- Do not expose credentials, cookies, tokens, raw exception payloads, or private source content in evidence artifacts.

### R2. Read-only provider preflight

- Run the existing AkShare readiness smoke with explicit real-network opt-in before any database write.
- Treat installation errors, DNS/network failures, upstream schema drift, empty universe results, and daily-bar failures as separate diagnostics.
- Stop the write phase when the universe preflight cannot establish a usable provider response.

### R3. Full-universe synchronization acceptance

- Upgrade the acceptance database to Alembic head and start API, worker, and Redis successfully.
- Enqueue the universe sync through the public API/TaskRun path rather than calling the service as the only proof.
- Confirm the terminal TaskRun state, progress, provider/source metadata, reconciliation history, and active/provider-managed counts.
- Confirm the accepted universe contains non-empty SSE, SZSE, and BSE subsets with normalized unique symbols.
- Capture upstream count and exchange distribution as observed evidence; do not hard-code a market total that will become stale.
- Exercise or deterministically simulate an empty/incomplete follow-up snapshot and prove the last good active universe and manual rows are preserved.

### R4. Corporate-action batch acceptance

- Use a recent completed report period with provider-visible data.
- Execute at least two consecutive cursor batches through the API/worker path for `dividend_bonus` and `rights_allotment`.
- Verify stable ordering, `next_cursor`, terminal completion semantics, persisted-row counts, deterministic deduplication, retry diagnostics, and partial-success behavior.
- Re-run an accepted batch and prove it does not create duplicate evidence rows or unstable citation IDs.

### R5. Full-universe discovery acceptance

- Execute all three profiles: `balanced_research`, `quality_value`, and `trend_liquidity`.
- Confirm `candidate_scope` covers the complete stored active CN stock universe and the final shortlist bound does not cap evaluation scope.
- Capture elapsed time, query count or equivalent database instrumentation, evidence coverage, matched/returned counts, compact diagnostics, and missing-evidence reasons.
- Validate deterministic shortlist stability for identical stored evidence and inputs.
- Validate that disabled/unconfigured LLM use falls back deterministically.
- When an OpenAI-compatible provider is configured, validate that unknown citation IDs or unknown candidate symbols are rejected and cannot alter membership or ranking. Live LLM access is optional; the safety contract is mandatory.

### R6. UI and operational acceptance

- Verify `/ai-research`, `/evidence`, and linked TaskRun detail pages at desktop and mobile widths.
- Confirm refresh, polling, profile selection, discovery, cursor continuation, degraded/error messages, citations, and “Use in desk” behavior.
- Capture durable screenshots and browser console/network observations without secrets.
- Confirm that stalled/failed tasks expose an actionable retry path and that no page labels mock, unavailable, or partial data as live/complete.

### R7. Targeted hardening

- Classify every finding as product defect, provider limitation, environment/configuration issue, or accepted data gap.
- Implement only fixes required for R1-R11 acceptance or repeatable operator diagnosis.
- Add regression tests for every corrected product defect.
- Update the runbook with reproducible commands, expected evidence, abort conditions, cleanup, and retry guidance.
- Preserve research-only, no-investment-advice, and no-automated-trading boundaries.

### R8. Resumable full-market evidence backfill

- First validate the real provider path with a bounded 50-100 symbol cohort containing SSE, SZSE, and BSE instruments.
- Add a production-safe backfill job over the stored active A-share universe for daily bars, latest fundamentals, and derived daily technical indicators.
- Use deterministic symbol ordering, bounded batches, a stable cursor/checkpoint, per-symbol status, progress reporting, partial-success persistence, retryable failures, and idempotent replay.
- Separate provider fetch phases from local indicator calculation so local retries do not repeat successful network work unnecessarily.
- Use a default rolling daily-bar horizon of 18 calendar months (approximately 350-380 trading sessions), while keeping the explicit start/end dates in task inputs and result metadata.
- Make the selected history horizon, batch size, provider, universe snapshot/revision, and requested evidence kinds explicit task inputs and stored result metadata.
- Support aborting and resuming without clearing successful rows or restarting from symbol zero.
- Record coverage by evidence kind and exchange; missing or failed evidence remains a visible gap and never becomes a passing criterion.
- Acceptance requires every in-scope symbol to reach a classified terminal outcome, at least 95% daily-bar coverage, at least 90% technical-indicator coverage, and at least 80% latest-fundamental coverage, with no exchange wholly missing.
- Falling below a threshold must produce a partial/needs-attention result with retained checkpoints and a retry set rather than a false success.
- Do not make a several-thousand-symbol backfill a single synchronous API request or a single opaque Celery loop without checkpoints.

### R9. Recurring incremental freshness

- Configure Celery scheduling explicitly for `Asia/Shanghai`; schedule labels and result metadata must state the effective timezone.
- Refresh daily bars and derived technical indicators after the A-share close, defaulting to 18:30 on trading days.
- Use a 10-calendar-day overlapping daily-bar window so holidays and short outages can be repaired idempotently without rerunning the 18-month baseline.
- Refresh latest fundamentals through deterministic daily shards covering approximately one fifth of the active universe per day.
- Reuse the same checkpoint, partial-success, retry-set, coverage, and provider-diagnostic contracts as the initial backfill.
- Do not launch another scheduled run when the same evidence-kind/universe run is still active; report the overlap decision explicitly.
- Keep the existing daily universe synchronization, but make its timezone and relationship to evidence checkpoints explicit.

### R10. AI Research operations UI

- Extend `/ai-research` with full-market evidence coverage and exchange distribution for daily bars, fundamentals, and indicators.
- Show current run kind, status, batch/cursor progress, elapsed time, failed/no-data counts, latest refresh, provider, and threshold evaluation.
- Provide guarded actions for initial backfill, resume, and retry-failed operations through typed Web proxy routes.
- Preserve API/CLI entry points for automation and maintenance.
- Do not expose evidence deletion, database reset, secret values, raw exception dumps, or unrestricted arbitrary task inputs in the UI.
- Use existing TaskRun detail links and source/degraded labels instead of creating a second incompatible task-status model.

### R11. Provider provenance and extension boundary

- The first real backfill and acceptance path uses AkShare explicitly.
- Backfill/task/storage/coverage contracts remain provider-neutral so another provider can be added without replacing checkpoint or UI semantics.
- Every persisted evidence and coverage result records the effective provider and source.
- AkShare failure or no-data must not silently fall back to yfinance, Tushare, mock, static fixtures, or another source.
- Multi-provider reconciliation, cross-source conflict policy, paid entitlements, and Tushare credentials are follow-up work.

## Acceptance Criteria

- [x] AC1: A reproducible acceptance record identifies commit, environment, migration head, provider, execution window, and sanitized commands.
- [x] AC2: The non-mutating AkShare preflight produces a classified pass/fail result before database writes.
- [x] AC3: A public API request reaches a real Celery worker, completes a real universe sync, and records TaskRun progress/result metadata.
- [x] AC4: The stored active universe has non-empty SSE/SZSE/BSE coverage, unique normalized symbols, and an auditable reconciliation history.
- [x] AC5: A failed/empty/incomplete follow-up cannot erase the last good universe or manual instruments.
- [x] AC6: Two or more real corporate-action cursor batches persist eligible data, continue deterministically, surface partial failures, and remain idempotent on replay.
- [x] AC7: Each named discovery profile evaluates the full stored scope and reports timing, coverage, shortlist counts, and compact missing-evidence diagnostics.
- [x] AC8: Repeated discovery over unchanged evidence preserves deterministic membership/ranking, and AI/fallback output cannot introduce unknown citations or symbols.
- [x] AC9: Desktop/mobile browser evidence covers the AI Research, Evidence Center, and TaskRun flows with no uncaught console errors or misleading source state.
- [x] AC10: Any in-scope fixes have focused regression tests; backend, Web, type, migration, and Trellis checks pass.
- [x] AC11: The operator runbook documents setup, safe execution, abort/rollback, retry, evidence capture, and cleanup.
- [x] AC12: Findings that require new paid providers, credentials, broad corpus ingestion, or unrelated professional-terminal features are documented as follow-up work rather than silently expanded into this task.
- [x] AC13: A 50-100 symbol SSE/SZSE/BSE canary cohort completes the daily-bar, fundamental, indicator, screening, and retry path with recorded coverage.
- [x] AC14: The full-market backfill can process bounded deterministic batches, resume from a stored checkpoint, retry failed symbols, and replay completed work idempotently.
- [x] AC15: Full-market coverage reports separate daily bars, fundamentals, indicators, no-data, provider failures, and exchange distribution rather than reporting one ambiguous success count.
- [x] AC16: Asia/Shanghai schedules refresh daily bars/indicators with a 10-day overlap and rotate fundamentals through deterministic daily shards without rerunning the full baseline.
- [x] AC17: Scheduled overlap protection prevents duplicate active runs and records whether a run was started, skipped, resumed, or retried.
- [x] AC18: `/ai-research` exposes tested coverage, progress, resume, and retry-failed controls with desktop/mobile states and links to the authoritative TaskRun details.
- [x] AC19: The first run is explicitly AkShare-backed, every result exposes provider/source provenance, and provider failure cannot trigger a silent fallback.

## Out of Scope

- Announcement, filing, annual-report, transcript, or brokerage-research corpus ingestion.
- New ranking models, natural-language rule generation, automatic trading, broker integration, or portfolio allocation.
- Production Level-2, realtime WebSocket feeds, or provider entitlement procurement.
- General dashboard redesign, backtesting UI, saved screeners, configurable workstations, or portfolio risk analytics.
- Treating a single successful provider response as a formal provider SLA.
