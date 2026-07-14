# Simplify LLM API configuration

## Goal

Make the existing OpenAI-compatible LLM integration safe and easy to configure
for a personal research installation. The current DeepSeek endpoint must use the
configured model instead of the provider's hard-coded OpenAI model, while all
existing deterministic fallbacks and research safety boundaries remain intact.

## Background

- The local ignored settings file currently selects the OpenAI-compatible
  provider, uses `https://api.deepseek.com/v1`, and has a configured key, but it
  has no model field.
- `packages/ai/provider.py` always sends `gpt-4o-mini`, which is inconsistent
  with the configured DeepSeek endpoint and matches the sanitized
  `HTTPStatusError` seen in the latest live acceptance.
- Python and Next.js both read and rewrite `data/platform_settings.json`, so a
  new field must be implemented on both sides or one writer will drop it.
- Public settings currently return the full LLM key, and the settings page puts
  it into the password input's HTML value. This violates the repository's
  existing no-secret public payload boundary.
- The Model API card is below the large news-provider section and exposes only
  the technical `mock` / `openai` values, requiring the user to know the base
  URL and model conventions manually.

## Requirements

### R1. Configurable OpenAI-compatible model

- Add `llm_model` to environment defaults, Python settings, Next settings, the
  FastAPI settings request/response, both Next settings aliases, the settings
  Server Action, the LLM factory, and the HTTP provider.
- Keep the persisted provider values limited to `mock` and `openai`.
  DeepSeek remains an OpenAI-compatible preset, not a new provider adapter.
- Existing settings without `llm_model` resolve to `gpt-4o-mini`.
- Trim model and base URL values. A custom base URL must be an absolute HTTP or
  HTTPS URL without credentials, query parameters, fragments, or an invalid
  port, and a custom model must be non-empty.

### R2. Focused settings experience

- Move the existing Model API card near the top of the Settings page.
- Replace the technical provider selector with an API preset selector:
  - disabled -> `mock`
  - DeepSeek -> `openai`, `https://api.deepseek.com/v1`, `deepseek-chat`
  - OpenAI -> `openai`, `https://api.openai.com/v1`, `gpt-4o-mini`
  - custom OpenAI-compatible -> validated model and base URL fields
- Keep API key entry visible and put model/base controls under progressive
  disclosure. Custom configurations open the advanced section initially.
- Show the user-facing preset and configured-key state instead of only the
  internal provider value.
- Keep the existing server-rendered page and Server Action; do not add a client
  settings wizard, global state, or a new page.
- Invalid custom URL, missing custom model, or first-time external setup without
  a key returns a localized field-level error with a stable code and
  `role="alert"`. Existing success/error flash feedback remains available.

### R3. Secret-safe public settings

- Python and Next public settings always return `llm_api_key: ""`.
- Public settings retain `llm_api_key_configured` so the UI can show status.
- The settings page never pre-fills the saved key into HTML.
- Submitting a blank key preserves the existing private key; a non-blank key
  replaces it.
- Error payloads, tests, evidence, logs, and task artifacts must not contain the
  key or authorization header.

### R4. Accurate model metadata

- Successful model-backed market assistant, dashboard brief, saved research
  brief, source ingestion, and stock-discovery responses identify the configured
  physical model in `model.name`.
- Fallback model names, `used_llm`, `fallback_reason`, citation validation,
  shortlist symbol validation, and deterministic behavior remain unchanged.
- New persisted records use accurate model metadata. Existing research briefs
  and shortlists remain immutable and are not migrated.

### R5. Compatibility and personal-use boundary

- No database schema change is required.
- The current local DeepSeek configuration is updated to `deepseek-chat` after
  rollout without printing or returning its key.
- The 95/90/80 evidence thresholds and deterministic shortlist membership,
  score, and rank are unchanged.
- Existing callers that omit `llm_model` keep the OpenAI default and fallback
  behavior.

## Acceptance Criteria

- [x] DeepSeek and OpenAI presets save the exact provider/base/model mappings;
      custom input is trimmed and validated; disabled mode uses `mock`.
- [x] Legacy settings without `llm_model` load as `gpt-4o-mini`, and a settings
      save round-trips `llm_model` through both Python and Next writers.
- [x] A fake HTTP request proves the provider sends the configured `model` and
      normalized base URL.
- [x] Python settings API and both Next settings routes never return the raw
      LLM key on GET or PUT and still report configured state.
- [x] Missing/blank legacy bases keep the compatibility default, while an
      invalid non-empty stored or environment base disables external execution
      and requires a replacement key instead of rerouting the existing key to
      another host.
- [x] Blank key updates preserve the existing key, while replacement remains
      supported without exposing the stored value.
- [x] The Settings page renders the preset, model, advanced base URL, configured
      key guidance, localized validation errors, and no key value in the input.
- [x] Successful LLM service tests report the configured model; all existing
      fallback, citation, symbol, ranking, and safety tests continue to pass.
- [x] Full backend and web suites, touched Ruff/mypy, TypeScript, Trellis
      validation, JSON parsing, and `git diff --check` pass.
- [x] Live DeepSeek canaries for stock discovery and `/assistant/market` return
      `used_llm=true`, `fallback_reason=null`, `model.name=deepseek-chat`, and
      only valid citations; discovery membership, order, and scores match the
      deterministic control. After the user refreshed the configuration on
      2026-07-14, each paid path passed on its first call with no retry.
- [x] Frontend/API health remains OK after worker/API reload.

## Out of Scope

- Provider registry or a persisted `deepseek` provider type.
- Model discovery, quota/cost dashboards, streaming, multiple profiles/keys,
  secret-manager or encryption infrastructure.
- A connection-test endpoint or automatic paid requests from the settings page.
- New research inputs, ranking rules, prompts, data sources, pages, permissions,
  trading features, or relaxed evidence/citation gates.
