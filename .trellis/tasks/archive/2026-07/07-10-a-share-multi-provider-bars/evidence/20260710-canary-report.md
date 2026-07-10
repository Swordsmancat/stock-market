# A-share Multi-Source Daily-Bar Canary Report

- Execution: 2026-07-10 23:08 CST
- Application commit: `58e8a9158cd94381c19274d085623367b6b2b25c`
- Runtime: isolated `stock-acceptance` Compose project
- Database: `stock_acceptance`, Alembic `0016_daily_bar_provenance`
- Policy: `cn_resilient`
- Database writes: isolated acceptance database only

## Results

| Check | Result | Evidence |
|---|---|---|
| Read-only preflight | PASS | Eastmoney `ConnectionError`; Sina selected with usable qfq rows |
| Full A-share universe | PASS | 5,530 active instruments across SSE/SZSE/BSE |
| 50-symbol canary task | PASS | Terminal TaskRun `succeeded` |
| Daily-bar canary coverage | PASS | 50/50 symbols, 16,424 rows |
| Persisted source | PASS | `akshare.stock_zh_a_daily`, 50 instruments |
| Discovery replay | PASS | All three profiles stable across two executions |
| Corporate-action slice | PASS | Two batches and one replay succeeded |
| Browser source visibility | PASS | Policy, Sina source mix, and controlled fallback visible; no console warnings/errors |

The full-market coverage payload remains `needs_attention` because only the
bounded 50-symbol canary has been populated out of 5,530 instruments. This is
the correct threshold state and is not reclassified as success.

Sanitized machine artifacts:

- `../a-share-live-acceptance/evidence/20260710T145814Z-preflight.json`
- `../a-share-live-acceptance/evidence/20260710T150816Z-canary.json`

The full baseline was not started automatically after the canary. The Sina
endpoint is a bulk-call-sensitive public source; the resumable full baseline
should be scheduled as a separately monitored operation with retained
checkpoints rather than extending this bounded feature acceptance run.
