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
- The active A-share evidence backfill was not interrupted for rollout. At the
  final audit it was healthy in `daily_bars` at cursor `2725/5530`, with a
  fresh heartbeat, four sanitized per-symbol processing diagnostics, and one
  retry item. The primary AkShare source remained circuit-open while the
  controlled secondary AkShare source continued producing rows; the solo
  Celery worker and Beat were not restarted.

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
