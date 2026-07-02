# Provider settings and readiness visibility - Design

## Summary

This task makes provider selection trustworthy before adding larger market-data display workflows. The core fixes are:

- omitted provider parameters should resolve to platform settings;
- public settings responses should not expose provider secrets;
- provider capabilities should be visible without live network checks;
- settings UI should show which provider is active and what it can do.

## Backend design

### Provider resolution

`packages.services.market_data.resolve_market_data_provider_name()` should accept `None` as the default requested provider. A non-empty requested provider remains authoritative. An omitted provider resolves through `get_effective_market_data_provider(None)`.

Market-data router query parameters should use `provider: str | None = Query(default=None)` so platform settings are honored when callers omit provider.

### Public settings safety

`packages.services.platform_settings.get_platform_settings_public()` should expose secret configuration state instead of secret values:

- `tushare_token_configured: boolean`
- `tushare_token: ""`

The current LLM key behavior is not changed in this task because the PRD specifically targets market-data provider secrets. A later security task can mask all secrets consistently.

### Capability metadata

The backend should expose a deterministic provider capability list in public settings. This is static/local metadata and must not hit provider networks.

Each provider capability should include:

- provider name;
- whether it is the active provider;
- whether it is configured enough to attempt use;
- whether it supports daily bars;
- whether it supports true real-time quotes;
- provider category such as `mock` or `historical_daily`;
- short readiness notes.

## Frontend design

The settings page should render the active provider and a capability/readiness summary. The page should not prefill the Tushare token value into client HTML; it should show a configured placeholder instead.

The frontend local settings store should mirror the backend capability metadata shape because the current settings page reads the shared JSON file directly.

## Test design

- Backend service tests cover omitted-provider defaulting and explicit provider override.
- Backend/API settings tests cover Tushare token masking and capability metadata.
- Frontend tests cover settings capability display if nearby settings page tests exist; otherwise keep validation to type-safe rendering and existing API proxy tests.

## Non-goals

- No real-time quote implementation.
- No live provider network checks in CI.
- No database schema migration.
