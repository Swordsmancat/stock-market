# Strict homepage reference redesign

## Goal

Rebuild the StockAI Hub homepage so the first viewport follows the supplied dark fintech terminal reference image as a concrete layout specification, not just a general style direction.

The user-facing value is a dense, scan-first market cockpit: index movement, macro indicators, sector heat, news sentiment, market overview, fund flow, AI sentiment, and news-source readiness should all be visible as aligned terminal panels on desktop.

Reference image:

- `C:\Users\ADMINI~1\AppData\Local\Temp\codex-clipboard-770843f8-7048-45e8-88c5-86f2a007777b.png`

## Confirmed Facts

- The app shell already defaults first-run theme to dark in `apps/web/app/[locale]/layout.tsx`.
- The current homepage fetches the data needed for the MVP: market overview, index favorites, macro favorites, hot sectors, latest news, alerts, task status, and provider capabilities in `apps/web/app/[locale]/page.tsx`.
- The current homepage still renders a large overview hero and stacked sections before the main content. This is visible around `apps/web/app/[locale]/page.tsx:1078`, followed by separate core-index and macro sections around `apps/web/app/[locale]/page.tsx:1115` and `apps/web/app/[locale]/page.tsx:1192`.
- The current latest-news panel only renders `newsPayload.items[0]`, with `latestNews` assigned at `apps/web/app/[locale]/page.tsx:911` and displayed around `apps/web/app/[locale]/page.tsx:1297`.
- The provider strip already reads `platformSettings.news_search_provider_capabilities` at `apps/web/app/[locale]/page.tsx:986` and renders provider cards around `apps/web/app/[locale]/page.tsx:1403`.
- Project frontend guidelines require homepage scope to remain curated: top ticker, index cards, macro favorites, hot sectors, latest news sentiment, compact status, and provider readiness only. Deep AI research, recommendations, reports, K-line workspaces, and trading flows stay off the homepage.
- Provider readiness is a status signal only. The homepage must not expose provider keys, and search results are citable only after local storage.

## Requirements

- Replace the oversized homepage hero with a reference-like top market band containing compact controls, an A-share/market title, add/settings action, and two grouped ticker lanes.
- Arrange the desktop first viewport as an aligned terminal grid:
  - Row 1: macro indicators table, hot sectors table, latest news sentiment list.
  - Row 2: market overview line chart, fund-flow bar chart, AI market sentiment gauge.
  - Bottom strip: dense news source status row.
- Use compact panel chrome: thin borders, small headings, dark surfaces, table rows, tabular numbers, blue active controls, green/red movement values, and amber/red AI heat indicators.
- Render latest news as a ranked multi-row list from `newsPayload.items`, not as a single featured card.
- Render macro indicators and hot sectors in table-like rows, not large loose cards.
- Render a simple SVG line chart for market overview using existing index/followed bar data.
- Render a simple SVG bar chart for fund flow using existing hot-sector flow data or deterministic fallback rows.
- Render an AI sentiment gauge derived only from available local/readiness signals, clearly as dashboard sentiment/status rather than trading advice.
- Preserve existing homepage index preference behavior: `favorite_home_index_codes` controls ticker/card order, and `home_index_display_fields` still controls optional index metadata.
- Preserve existing backend/API contracts for this slice. Do not add automatic trading, new backend persistence, or new news-search API calls.
- Keep English and Chinese message files aligned for any new visible labels.

## Acceptance Criteria

- [ ] At a 1440x900 desktop viewport, the first content screen has no large hero block and visually follows the reference geometry: sidebar + top bar + ticker band + three top panels + three lower panels + provider strip.
- [ ] The homepage includes panel titles matching the reference concepts: macro indicators, hot sectors, latest news sentiment, market overview, fund flow, AI market sentiment, and news source status.
- [ ] The top ticker band shows grouped market controls and includes an `A股市场` label in Chinese locale or an English equivalent in English locale.
- [ ] Latest news renders multiple ranked rows when multiple news items are available, including sentiment/confidence metadata.
- [ ] Macro and hot-sector panels use compact table/list rows with stable row height and tabular numeric columns.
- [ ] Market overview and fund-flow panels render non-empty SVG visualizations when fixture data is present and useful empty states when not.
- [ ] AI sentiment panel renders a gauge-like visualization and supporting compact metrics without giving buy/sell/hold or execution guidance.
- [ ] News source status renders configured and needs-setup/degraded providers from `news_search_provider_capabilities` without exposing secrets.
- [ ] Existing index preference tests continue to prove configured index order and display-field behavior.
- [ ] Homepage tests prove deep modules are still absent from the homepage.
- [ ] `npm run test:web -- apps/web/app/[locale]/page.test.tsx apps/web/components/market-ticker.test.tsx --reporter=dot` passes.
- [ ] `git diff --check` passes.

## Out Of Scope

- Automatic trading, order placement, portfolio execution workflows, and trading instructions.
- Backend schema changes or new provider adapter implementation.
- Reworking all non-homepage pages to match the reference.
- Exact pixel-perfect replication of the screenshot assets; this slice targets strict layout, hierarchy, density, and visual language using the app's existing data and components.
