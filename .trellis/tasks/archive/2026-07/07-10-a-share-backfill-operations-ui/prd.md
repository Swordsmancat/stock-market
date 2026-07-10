# A-share Backfill Operations UI

## Goal

Expose the authoritative A-share evidence coverage and resumable backfill controls in AI Research so users can see whether deterministic stock discovery has sufficiently complete stored evidence.

## Requirements

- Fetch `GET /stock-selection/evidence-coverage` with no-store semantics and render overall plus SSE/SZSE/BSE bar, indicator, and fundamental coverage.
- Show threshold results, provider, as-of, latest run kind/status/phase/cursor, processed count, heartbeat, retry counts/previews, and sanitized diagnostics.
- Provide guarded canary and baseline starts, resume, retry-failed, and cooperative cancel actions through Next.js proxy routes.
- Poll authoritative coverage while the latest run is queued/running/cancel-requested and stop polling in terminal states.
- Link the latest run to its existing TaskRun detail when available.
- Keep loading, empty, partial, threshold-failed, provider/error, and success states distinct.
- Add English and Chinese translations together; keep desktop/mobile layouts accessible and dense.
- Do not expose delete/reset, database controls, arbitrary symbols, secrets, or raw upstream exceptions.

## Acceptance Criteria

- [x] Server-rendered AI Research receives initial evidence coverage without caching.
- [x] Coverage and exchange breakdown render correctly with thresholds and source state.
- [x] Start/resume/retry/cancel interactions forward typed requests and refresh authoritative state.
- [x] Baseline and cancel actions require explicit browser confirmation.
- [x] Active runs poll; terminal runs do not continue polling.
- [x] TaskRun links use the backend-provided ID.
- [x] Proxy routes preserve upstream status, content type, payload, and no-store headers.
- [x] Component, proxy, page, locale, TypeScript, full Web tests, Trellis validation, and `git diff --check` pass.

## Out of Scope

- Backend contract changes, live-network execution, evidence deletion, provider credentials, multi-provider reconciliation, or trading.
