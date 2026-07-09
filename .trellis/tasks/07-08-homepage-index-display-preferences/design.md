# 首页核心指数自选展示参数 - Design

## Architecture And Boundaries

- Scope stays inside `apps/web`; no backend API or database schema changes.
- Persist preferences through the existing server-side platform settings file at `data/platform_settings.json`, using `apps/web/lib/platform-settings-store.ts`.
- Keep the homepage as a Server Component. Do not add a global client store, React Query, browser localStorage, or account-level sync.
- Keep the existing curated homepage boundary: index preferences tune the current index surfaces only; they do not introduce new homepage modules.

## Settings Contract

Add two public platform settings fields:

- `favorite_home_index_codes: string[]`
- `home_index_display_fields: HomeIndexDisplayField[]`

Recommended field union:

```ts
export type HomeIndexDisplayField =
  | "latest_close"
  | "percent_change"
  | "freshness"
  | "as_of"
  | "region"
  | "provider";
```

Recommended defaults:

```ts
export const DEFAULT_FAVORITE_HOME_INDEX_CODES = [
  "us_sp_500",
  "us_nasdaq_composite",
  "us_dow_jones",
  "cn_shanghai_composite",
  "cn_shenzhen_component",
  "cn_csi_300",
  "cn_chinext",
  "cn_csi_500",
] as const;

export const DEFAULT_HOME_INDEX_DISPLAY_FIELDS = [
  "latest_close",
  "percent_change",
  "freshness",
  "as_of",
  "region",
] as const;
```

Normalization rules:

- Accept arrays and newline/comma-separated strings for `favorite_home_index_codes`.
- Trim values, drop empty entries, and dedupe while preserving first occurrence order.
- Accept arrays and comma/newline strings for `home_index_display_fields`.
- Drop unknown display-field values.
- If `home_index_display_fields` normalizes to an empty array, fall back to `DEFAULT_HOME_INDEX_DISPLAY_FIELDS`.
- If `favorite_home_index_codes` normalizes to an empty array, public settings should expose defaults so the homepage does not disappear after an empty save.

Compatibility:

- Existing `platform_settings.json` files without the new keys must still load successfully.
- Existing sensitive fields (`llm_api_key`, `tushare_token`) must keep their current preservation/masking behavior.
- The public settings route may expose these non-sensitive preference arrays.

## Homepage Data Flow

Current flow:

`getPlatformSettings()` -> `/dashboard/market-overview` -> `marketOverviewPayload.indices.items` -> `tickerItems` and `coreMarketIndexItems`

New flow:

1. Read `platformSettings.favorite_home_index_codes`.
2. Build an ordered list of homepage index rows from `marketOverviewPayload.indices.items`.
3. For each configured code:
   - If present in payload, use the payload item.
   - If missing, create a UI placeholder row with the configured code and `status`/`freshness` degraded enough to render an explicit unavailable card.
4. If configured list is empty, use defaults from `DEFAULT_FAVORITE_HOME_INDEX_CODES`.
5. Use the resulting ordered rows for both:
   - Top `MarketTicker`
   - "Core market indices" cards

This keeps the two homepage index surfaces consistent.

## Missing Index Behavior

Missing configured codes should be visible rather than silently ignored:

- Card title can fall back to the code.
- Price and percent fields render the existing unavailable label.
- Freshness renders unavailable/no-data style.
- Optional message should explain that the configured index was not present in the market overview payload.

Do not fake `latest.close`, movement, source, or as-of dates.

## Display Field Behavior

The card renderer should check `platformSettings.home_index_display_fields` before showing optional pieces:

- `latest_close`: latest price number.
- `percent_change`: percent movement.
- `freshness`: freshness badge.
- `as_of`: as-of date row.
- `region`: region label.
- `provider`: provider/source row, using available payload provider/effective provider/source data.

Keep the card grid stable when fields are hidden. Do not let cards collapse into awkward tiny tiles on desktop or overflow on mobile.

`MarketTicker` should keep its compact market-strip fields for scan speed; `home_index_display_fields` applies to the core cards only unless implementation finds a low-risk way to hide provider-like metadata in the ticker without harming layout.

## Settings UI

Add a Settings page card near "Homepage Macro Favorites":

- Title: Homepage core indices.
- Description: choose ordered US/A-share index codes shown in the homepage ticker and core index cards.
- Textarea for `favorite_home_index_codes`, matching macro favorites behavior.
- Checkbox list for `home_index_display_fields`.
- Default hint showing the recommended default codes and default fields.

Use translated strings from `apps/web/messages/en.json` and `apps/web/messages/zh.json`. Avoid raw JSON examples in message values because `next-intl` treats braces as ICU arguments.

## Tests

Focused tests should cover:

- Store normalization for strings, arrays, dedupe, unknown display fields, and empty fallbacks.
- `savePlatformSettingsAction` forwards the new form fields to `savePlatformSettings`.
- Settings route tests include the new non-sensitive arrays in returned/saved payload expectations where exact payloads exist.
- Homepage renders configured index order for both ticker/core cards.
- Missing configured code renders an unavailable state rather than disappearing.
- Homepage still does not render deep modules.

## Rollback

Rollback can remove the two settings fields and Settings UI card while keeping the curated homepage redesign intact. Existing `platform_settings.json` files with extra keys are harmless if readers ignore unknown fields.
