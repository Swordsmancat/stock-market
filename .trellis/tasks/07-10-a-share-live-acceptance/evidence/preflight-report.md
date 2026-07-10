# A-share Live Acceptance Preflight Report

- Execution time: 2026-07-10 19:25 CST (11:25 UTC)
- Application base commit: `8d99577902d13045ddab658b8aed9e2742841cbf`
- Working tree: dirty (acceptance harness under implementation)
- Python: 3.13.7
- AkShare: 1.18.64
- Alembic head: `0015_research_evidence_backfills`
- Provider / market: AkShare / CN
- Database writes: none

## Results

| Check | Result | Sanitized evidence |
|---|---|---|
| Full A-share universe | PASS | 5,530 instruments; SSE 2,308, SZSE 2,895, BSE 327 |
| 600519 daily bars | FAIL | Three bounded attempts ended with `ConnectionError` |
| Write gate | PASS | Canary, migrations, and baseline were not started |

## Classification

- `provider_limitation` / `environment_configuration`: the AkShare universe
  endpoint is usable, while the daily-bar endpoint repeatedly resets the
  connection in the current network window.
- No evidence supports classifying the bar failure as valid no-data or as a
  stored-data/product defect.
- The isolated write phase remains blocked by design until the same read-only
  preflight succeeds. No provider substitution or threshold change is allowed.

## Next safe action

Re-run:

```bash
python scripts/a_share_live_acceptance.py --phase preflight --real-network
```

Only after both checks pass may the operator start the `stock-acceptance`
Compose stack and run the guarded canary command from the runbook.
