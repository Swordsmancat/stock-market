# LLM API configuration acceptance

Date: 2026-07-14 (Asia/Shanghai)

## Automated quality gates

- Backend: `826 passed`.
- Web: `81` files and `265` tests passed.
- TypeScript: `npx tsc -p apps/web/tsconfig.json --noEmit` passed.
- Ruff: all touched Python implementation and test files passed.
- Targeted mypy: settings router/store and LLM factory passed with imported
  modules skipped so unrelated repository-wide type debt does not mask this
  task's result.
- English and Chinese message catalogs parsed as UTF-8 JSON.
- Trellis task validation and `git diff --check` passed.
- Independent final review found no remaining actionable issue after verifying
  Python/Next URL parity, malformed persisted JSON, host/key association, and
  fail-closed provider behavior.

## Runtime and UI acceptance

- `http://localhost:3000/zh/settings` and `http://localhost:8000/health`
  returned HTTP 200 after rollout.
- FastAPI and both Next settings aliases returned `llm_model=deepseek-chat`,
  `llm_api_key=""`, and `llm_api_key_configured=true`.
- Credential-bearing Base URLs and non-object settings payloads returned a
  secret-safe HTTP 422 without echoing the submitted value.
- Missing/blank legacy base/model fields use the validated environment default.
  Invalid explicit or non-string bases disable external execution and make the
  associated key non-reusable; changing hosts without a replacement key clears
  the old key at both writer boundaries.
- Desktop (1440x1000) and mobile (390x844) checks showed no horizontal
  overflow. The page selected the DeepSeek preset, left the password input
  empty, displayed the configured-key guidance, and kept advanced fields
  collapsed for the built-in preset.
- The A-share incremental backfill continued in the normal personal `stock`
  database, not the stopped `stock-acceptance` stack. It reached checkpoint
  `4650/5530` before its provider call exceeded the configured 30-minute stale
  threshold. Cooperative cancellation preserved the checkpoint and rows. The
  blocked solo worker was replaced without restarting API, Web, Beat, or the
  database; the backfill then reached `cancelled` and its TaskRun reached
  `succeeded`.
- Beat's already queued normal rotation then ran fundamental shard `1/5` as the
  sole active AkShare backfill. It completed `1106/1106` with `1103` successes,
  three valid no-data results, zero failures, and no diagnostics.
- Final personal coverage remained `ok`: daily bars `5508/5530` (`99.60%`),
  technical indicators `5516/5530` (`99.75%`), and fundamentals `5530/5530`
  (`100%`). All fixed `95/90/80` gates pass, all SSE/SZSE/BSE universe counts
  are present, and active backfill count returned to zero. No extra technical
  baseline or fundamental shards were started because they would add redundant
  provider load.
- Sanitized terminal evidence:
  `evidence/20260714T140010Z-personal-coverage-terminal.json`.

## Live DeepSeek canaries

Each paid path was called once. No retry was made after failure.

### Stock discovery

- Deterministic and LLM requests returned the same 10 shortlist members in the
  same rank/score order; the first symbol was `920946`.
- Citation allowlisting and deterministic-shortlist safety remained intact.
- The live response degraded to `deterministic-stock-discovery-v1`; it did not
  satisfy `used_llm=true` or `model.name=deepseek-chat`.

### Market assistant

- Stored AkShare evidence was available and three citations were assembled.
- The live response safely degraded with
  `LLM generation failed: HTTPStatusError.`
- Diagnostics remained sanitized and no API key, authorization header, raw
  provider body, or answer text was recorded here.

## Result

The implementation, security, deterministic behavior, metadata propagation,
and local runtime rollout passed. Successful external DeepSeek generation is
blocked by the current upstream credential, quota, or account state. The live
success acceptance item remains open; thresholds and citation/symbol gates were
not weakened.
