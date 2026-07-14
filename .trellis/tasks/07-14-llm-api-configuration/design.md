# LLM API configuration design

## Boundary

This task changes one existing configuration flow. It does not introduce a new
provider abstraction. The stored `llm_provider` remains the execution-mode gate
(`mock` or `openai`), while presets are a Settings-page convenience that resolve
to the existing OpenAI-compatible contract.

## Data flow

```text
Settings preset/form
  -> Next Server Action validation and preset resolution
  -> data/platform_settings.json
  -> Python/Next normalized private settings readers
  -> llm_factory(api_key, api_base, llm_model)
  -> OpenAICompatibleLLMProvider request
  -> validated service response/model metadata
```

Public projections are separate from private settings readers:

```text
private llm_api_key -> configured boolean -> public response
                    -> never serialized as the key value
```

## Configuration contract

- Python environment defaults own `llm_provider`, `llm_api_key`,
  `llm_api_base`, and `llm_model`.
- Python and TypeScript normalized settings include the same four fields.
- Default API base is `https://api.openai.com/v1`; default model is
  `gpt-4o-mini`.
- The DeepSeek UI preset resolves to the existing `openai` execution branch,
  `https://api.deepseek.com/v1`, and `deepseek-chat`.
- Missing legacy `llm_model` uses the default. The local runtime is explicitly
  saved with `deepseek-chat` during rollout rather than changing the global
  legacy default.
- Blank key updates preserve the private stored key. Public projections replace
  the key with an empty string after computing `llm_api_key_configured`.

## Settings interaction

The page stays server-rendered. The preset `<select>` is submitted with the
existing form. The Server Action resolves known presets and ignores stale
advanced values for them. Custom mode reads the submitted advanced fields,
trims them, validates an absolute HTTP(S) URL without embedded credentials,
query parameters, fragments, or an invalid port plus a non-empty model, and
redirects with a stable error code on failure.

The Model API card moves before the provider-specific/news sections. It shows:

- preset selector with user-facing names;
- API key password field that is always blank on render;
- configured/unconfigured helper text;
- native `<details>` containing model and base URL, open initially for custom
  configurations;
- a localized inline `role="alert"` for validation failures.

This avoids client state, a new endpoint, and automatic paid test requests.

## Model execution and metadata

`OpenAICompatibleLLMProvider` receives the normalized model in its constructor
and sends it in `chat/completions`. Services that currently report a hard-coded
physical model read the same normalized setting for successful metadata.
Logical/fallback identifiers remain unchanged where they describe deterministic
pipelines.

The stock-discovery success metadata uses the physical configured model so a
persisted daily shortlist records which external model explained the fixed
cohort. Validation continues to reject added symbols or unknown citations, so
the model cannot change membership or rank.

## Error and security behavior

- Form validation errors are localized and field-adjacent.
- Direct settings services normalize whitespace and retain backward defaults.
- Missing/blank legacy bases retain the backward default, while non-empty
  invalid persisted or environment bases force `mock` so an existing key can
  never be rerouted to the default OpenAI host. That key is treated as
  unconfigured until the user enters a replacement for a valid preset/base.
- Settings writers clear the old key when the normalized API host changes
  without a replacement key. The disabled preset updates only `llm_provider`,
  preserving the last valid host/model association for intentional re-enable.
- Provider/runtime failures retain existing sanitized exception-class fallback
  messages.
- No public settings response, HTML input, test snapshot, TaskRun, or acceptance
  evidence contains an API key.

## Rollout and rollback

1. Ship additive settings and redaction changes.
2. Save only `llm_model=deepseek-chat` into the ignored local settings file.
3. Reload API/worker processes so the constructor change is active.
4. Run deterministic and LLM canaries with identical discovery input.

Rollback is code revert plus restoring `llm_model` in the ignored settings file.
The deterministic fallback remains available throughout, so no data migration
or threshold change is needed.
