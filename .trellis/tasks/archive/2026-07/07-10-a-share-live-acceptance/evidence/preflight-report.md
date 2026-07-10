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

## 2026-07-10 20:11 CST retest

- Application commit: `b3909c80ec62f8d3164cb8a291e4aa6f5759dcaa`
- Working tree before execution: clean
- Universe result: PASS, unchanged at 5,530 instruments (SSE 2,308, SZSE
  2,895, BSE 327)
- Daily-bar result: FAIL, three bounded `ConnectionError` attempts
- Database writes: none
- Sanitized machine evidence:
  `20260710T121125Z-preflight.json`

The repeat failure confirms the write gate is behaving correctly. The canary,
corporate-action, discovery, and baseline mutation slices remain not started.

## Acceptance image build verification

- Initial build diagnosis: the repository context included the nested
  `apps/web/.next` and `node_modules` directories because the root ignore rules
  were not recursive.
- Regression fix: the generated dependency rules now use recursive patterns;
  the API and Web build contexts dropped to approximately 1.11 MB and 258 KB.
- Web dependency diagnosis: the lock file was generated with npm 11.17.0 while
  the Node 22 base image supplied npm 10.9.8, which rejected the optional SWC
  peer dependency layout during a clean `npm ci`.
- Reproducibility fix: `package.json` declares `npm@11.17.0`, and the Web
  acceptance image installs that exact version before `npm ci`.
- Verification: `docker compose -f docker-compose.acceptance.yml build api web`
  completed successfully for both `stock-acceptance-api:latest` and
  `stock-acceptance-web:latest`.
- Runtime/database writes: none; only images were built. The isolated stack was
  deliberately not started because the daily-bar preflight remains failed.

## Quality verification

- Python: 555 tests passed.
- Web: 68 test files / 204 tests passed.
- TypeScript: `tsc --noEmit -p apps/web/tsconfig.json` passed.
- Ruff: changed acceptance script/test files passed. The repository-wide scan
  still reports four pre-existing unused imports outside this change.
- Compose: configuration is valid; both images exist; acceptance container
  list is empty.
- Normal runtime: API health returned `ok`; Web was restored and returned HTTP
  200 on port 3000 after the local dependency refresh.
- Browser smoke: the home page redirected to `/zh`, rendered the `StockAI Hub`
  dashboard and primary navigation, and produced no browser console warnings or
  errors.
- Dependency audit: two moderate findings remain in Next's bundled PostCSS.
  npm offers only a breaking forced downgrade to Next 9.3.3, so no unsafe
  automated audit fix was applied.
- Evidence: JSON parses successfully and the evidence scan found no credential,
  authorization-header, cookie, database URL, Redis URL, or bearer-token text.
