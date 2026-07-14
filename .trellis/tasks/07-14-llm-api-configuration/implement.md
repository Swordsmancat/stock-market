# LLM API configuration implementation plan

## 1. Settings contract and secret projection

- Add environment/base/model defaults and normalization on Python and Next.
- Add `llm_model` to FastAPI and both Next route payloads.
- Redact `llm_api_key` in every public projection while preserving the
  configured flag and blank-update behavior.
- Add focused Python/TypeScript settings tests for defaults, round-trip,
  redaction, and preservation.

## 2. Provider request and response metadata

- Pass `llm_model` through `llm_factory` into
  `OpenAICompatibleLLMProvider`.
- Add a fake HTTP regression for base/model request identity.
- Replace successful hard-coded physical model metadata in market assistant,
  dashboard brief, research brief, source ingestion, and stock discovery.
- Keep fallback identifiers and all validation gates unchanged; update focused
  service expectations.

## 3. Settings-page usability

- Add pure TypeScript preset constants/inference shared by the page/action/store.
- Resolve presets and validate custom input in the existing Server Action.
- Move and rewrite the Model API card with preset selection, blank key input,
  configured helper, progressive advanced fields, and inline localized errors.
- Update English/Chinese messages and page/action/route/store tests.

## 4. Documentation and specification

- Document the LLM model/preset/redaction contract in the assistant research
  spec and the user-facing configuration path.
- Update `.env.example` with `LLM_API_BASE` and `LLM_MODEL`.
- Validate this task and run `git diff --check`.

## 5. Verification and live rollout

- Run focused backend and web tests during implementation.
- Run full backend/web suites, TypeScript, touched Ruff/mypy, and JSON parsing.
- Save `deepseek-chat` to the ignored local settings file without exposing the
  key, then reload affected API/worker processes.
- Compare deterministic and live-LLM stock discovery results; run one existing
  symbol through `/assistant/market`; verify model/citation/safety invariants.
- Confirm ports 3000/8000, Redis/Celery registration, and unchanged evidence
  thresholds.

## Rollback points

- Before runtime settings update: all changes are code-only and deterministic
  fallback remains active.
- Before process reload: restore the prior ignored settings file if focused
  tests fail.
- If the external provider fails live acceptance, keep the code and configured
  model, retain deterministic fallback, record sanitized evidence, and do not
  weaken validation.
