# Homepage terminal dashboard refactor

## Goal

Refactor the web homepage into a dark, dense financial terminal dashboard inspired by the provided reference image, while preserving the existing research-only market overview contracts and keeping deep workflows in their routed modules.

The first deliverable should make the homepage feel like an operational market console rather than a marketing page: compact left navigation, scan-first top market ticker, dense dashboard panels, tabular financial data, visible provider/source status, and restrained terminal styling.

Reference image: `D:/Administrator/Downloads/ChatGPT Image 2026年7月9日 10_31_34.png`.

## Confirmed Facts

- The project is a Next.js App Router frontend under `apps/web`.
- The current app shell already has `TopNavBar`, `SidebarNavigation`, `MobileNavigation`, breadcrumbs, backend status banner, and theme support.
- The homepage entry point is `apps/web/app/[locale]/page.tsx`.
- Project frontend guidelines define the homepage as a curated market overview, not a full research workspace.
- The homepage currently renders core index ticker/cards, macro favorites, hot sectors, latest news sentiment, and important status signals.
- Homepage core index order and displayed fields are configured through `favorite_home_index_codes` and `home_index_display_fields`.
- `MarketTicker` and homepage core index cards should keep using the same ordered index list.
- `getPlatformSettings()` exposes `news_search_provider_capabilities`, including provider display name, enabled/configured flags, implementation status, and priority.
- The current app shell uses `next-themes` with `defaultTheme="system"` and a theme toggle.
- User-visible text must stay localized in both `apps/web/messages/en.json` and `apps/web/messages/zh.json`.
- Product decision: first-run theme should default to dark terminal styling while retaining the theme toggle.

## Requirements

- Keep the MVP scoped to homepage-first frontend refactor plus only the shell styling needed to support the reference direction.
- Preserve existing backend endpoints, server-rendered data fetching, provider settings, homepage index preferences, and citation/source boundaries.
- Use the reference image as art direction: dark blue/black terminal surfaces, compact panels, blue active states, green/red market movement, tables, sparklines or chart-like visuals, and bottom provider/news-source status.
- Set the app's first-run theme default to dark, while retaining light/dark/system switching.
- Keep the homepage scan-first and dense. Do not add a landing-page hero or duplicate deep modules such as AI research briefs, full K-line workspaces, reports, technical indicators, or fundamentals.
- Reuse existing homepage data where possible: market overview, core indices, macro indicators, hot sectors, latest news, data health, alerts, and latest task run status.
- Add a homepage-facing news/provider status strip using existing settings/readiness data where available, with clear fallback states when detailed provider diagnostics are not present.
- Maintain accessibility: semantic headings, links/buttons for navigation/actions, keyboard-visible focus states, and readable contrast in dark mode.
- Maintain responsive behavior for desktop, tablet, and mobile without horizontal page overflow or overlapping text.
- Update affected homepage/page component tests and localized messages.

## Acceptance Criteria

- [ ] The homepage visually matches the reference direction as a dark, dense financial terminal dashboard.
- [ ] The first viewport prioritizes top ticker/index data and dashboard panels, not marketing copy.
- [ ] Core index ordering and display-field settings still affect both the ticker and core index cards.
- [ ] Macro indicators, hot sectors, latest news sentiment, and important status signals remain visible on the homepage.
- [ ] Deep modules remain off the homepage and continue to be reachable through navigation.
- [ ] News/provider status is visible on the homepage with configured/unconfigured/degraded-style states where data permits.
- [ ] English and Chinese message files remain aligned for any new visible text.
- [ ] Focused homepage/navigation tests pass.
- [ ] Full frontend test and type-check commands pass before completion, or any inability to run them is recorded.

## Out of Scope

- Automatic trading.
- Backend market-data or news-search provider implementation changes.
- Replacing the existing settings store or adding a global frontend state library.
- Full redesign of every routed module in this MVP.
- Introducing buy/sell/hold trading advice.

## Open Questions

- None blocking.
