# Homepage terminal dashboard refactor design

## Architecture and Boundaries

The implementation stays inside the Next.js frontend (`apps/web`) and does not change backend APIs, provider storage, citation rules, or server data contracts.

Primary files expected to change:

- `apps/web/app/[locale]/layout.tsx` for the first-run dark theme default and shell density tweaks.
- `apps/web/components/top-nav-bar.tsx`, `apps/web/components/sidebar-navigation.tsx`, and possibly `apps/web/components/mobile-navigation.tsx` for terminal-style navigation surfaces.
- `apps/web/components/market-ticker.tsx` for a denser top ticker with reference-like index cards and lightweight sparklines.
- `apps/web/app/[locale]/page.tsx` for the homepage dashboard grid and provider/news-source status strip.
- `apps/web/messages/en.json` and `apps/web/messages/zh.json` for new visible labels.
- Focused tests beside changed page/components.

The homepage remains a server-rendered curated market overview. Small visual helpers can live in the page file if they are homepage-specific. If a helper is shared by `MarketTicker` and homepage cards, it should be extracted to a component or local helper rather than duplicated.

## Data Flow and Contracts

Existing homepage server data remains the source of truth:

- Platform settings from `getPlatformSettings()`.
- Market overview from `/dashboard/market-overview`.
- Primary instrument latest/news/task/watchlist/alerts data from the current optional fetches.
- Hot sectors from `/sectors/hot?limit=5`.
- Official macro source status from `/market-indicators/official-sources/status`.

Core index preferences continue to flow through:

`platformSettings.favorite_home_index_codes -> buildHomeIndexItems() -> tickerItems + core cards`.

Display-field preferences continue to flow through:

`platformSettings.home_index_display_fields -> shouldShowHomeIndexField() -> core index card fields`.

News/provider status strip should use:

`platformSettings.news_search_provider_capabilities`.

The strip should show a compact ordered subset or horizontally scrollable list of providers with status derived from:

- `enabled`
- `configured`
- `credential_required`
- `credential_configured`
- `implementation_status`
- `priority`

No secret keys are exposed; public settings already redact `news_search_provider_keys`.

## Visual System

The MVP should implement a dark terminal financial dashboard:

- Default first-run theme: `dark`.
- Dense shell: darker top nav/sidebar, compact spacing, 8px-or-less card radius, subtle borders.
- Homepage grid: responsive terminal panels arranged as market ticker, core index cards, macro table, hot sector table, news sentiment list, market/status panels, and provider strip.
- Data visuals: lightweight SVG sparklines or bar/gauge-style CSS/SVG visuals using existing series/counts where available.
- Functional color: use existing market color helpers for green/red movement; use blue for active navigation and configured/primary states; use amber/red for degraded or unconfigured states.
- Avoid a marketing hero, large decorative gradients, decorative orbs, and card-in-card nesting.

## Compatibility and Migration

Changing `defaultTheme` to `dark` affects only first-run users without a saved theme. Existing users with a stored `next-themes` preference should keep their saved choice.

The theme toggle remains available so users can switch to light or system mode.

The homepage should preserve existing visible module ownership: deep AI research, reports, technical indicators, fundamentals, and K-line workspaces remain off the homepage and accessible through routes/navigation.

## Trade-offs

- Keeping the work homepage-first avoids a risky full-product redesign but means secondary routes may not fully match the new terminal polish immediately.
- Using existing provider capabilities avoids backend work but limits live quota/latency diagnostics to what settings already expose.
- Lightweight in-page visual helpers keep the MVP small; extract only if repeated logic appears across components.

## Rollback

Rollback is straightforward because the slice is frontend-only:

- Revert `defaultTheme` from `dark` to `system` if the default-theme change is too disruptive.
- Revert homepage layout/component changes without data migrations.
- Provider status strip can be removed without backend cleanup because it only reads public settings.
