# 前端整站重新美化 - Design

## Architecture And Boundaries

- Scope is limited to the Next.js frontend under `apps/web`.
- Preserve App Router structure, Server Components for data-heavy pages, existing route handlers, existing Server Actions, `next-intl`, Tailwind, and shadcn-style primitives.
- Do not introduce a global client state library. Keep existing ThemeProvider and MarketColorsProvider boundaries.
- Do not change backend API contracts unless a frontend state cannot be represented from existing payloads.

## Design System Shape

Use the generated UI/UX research as directional input, not as a file-to-code copy:

- Product category: Financial Dashboard.
- Target style: professional terminal density first, expressed as a Data-Dense Dashboard rather than a marketing or SaaS landing-page aesthetic.
- Third-wave user correction: the dashboard homepage must be a curated market overview, not a chart workspace or all-in-one research dashboard.
- Homepage priority order: core US/A-share indices, macro watchpoints, hot sectors, latest news sentiment, and only compact truly important operating status.
- Density: 8/10 for desktop financial workflows.
- Motion: standard/subtle; avoid slow or decorative animation.
- Colors: deep neutral surfaces plus semantic status colors; dark mode receives primary polish while light mode remains fully accessible.
- Typography: prioritize tabular numeric readability; current `Inter` can remain for body unless the implementation pass decides the Fira Sans/Fira Code swap is worth the layout risk.

Implementation should map this into existing shadcn CSS variables:

- `--background`, `--foreground`, `--card`, `--popover`, `--primary`, `--secondary`, `--muted`, `--accent`, `--destructive`, `--border`, `--input`, `--ring`.
- Add or document finance-specific semantic tokens only when Tailwind usage needs them repeatedly, for example positive/negative/warning/info/chart surface tokens.
- Keep `--radius` at or below the current 0.5rem; prefer crisp borders, low shadow, compact panels, and stable table-like surfaces.

## Shared Components

Upgrade shared components before rewriting pages one by one:

- `TopNavBar`: compact brand/search/actions layout, stable right actions, professional surface/border.
- `SidebarNavigation`: compact item rhythm, clearer active state, scroll behavior for 10+ nav items.
- `MobileNavigation`: avoid page-wide horizontal overflow; consider limiting top-level items or improving scroll affordance while preserving reachable routes.
- `FinancialPageHeader`: become the standard page identity and KPI strip for core routes; keep metrics serializable and testable.
- Dashboard homepage: use the top market strip plus a compact `FinancialDashboardHero`; keep deep workflows in their routed modules instead of expanding them on the homepage.
- UI primitives: adjust `Button`, `Card`, `Table`, `Input`, `Select`, `Tabs`, `Skeleton`, `Badge` only through established shadcn-style patterns.
- Domain panels: introduce small wrappers only if repeated page markup demands it, such as `DataPanel`, `MetricStrip`, or `DataTableShell`.

## Curated Homepage Direction

- Borrow product patterns, not protected branding: clean market strip, blue active states, readable index cards, and compact scan-first information hierarchy.
- Do not copy TradingView logos, names, exact layouts, screenshots, icons, or assets.
- Dashboard first viewport should make the product identity obvious without relying on a marketing hero: core indices first, followed by macro watchpoints, sector rotation, news sentiment, and compact status.
- Do not place AI research briefs, source-readiness workflows, recommendations, comparison tools, followed K-line tables, reports, technical indicators, or fundamentals on the homepage. Link to their owning modules instead.
- Keep existing payloads and truthful data states; empty market data states must remain explicit instead of drawing fake values.
- Keep the broader app consistent through shell, navigation, page header, card, and table updates rather than styling the dashboard alone.

## Page Migration Plan

Page migration should happen in waves to keep review and rollback simple:

1. Global shell, tokens, and shared primitives.
2. Existing partially unified pages: Dashboard, Watchlist, Settings, Instrument Detail.
3. Data-list pages: Instruments, Reports, Alerts, Task Runs, Portfolios.
4. Research-heavy pages: AI Research, Evidence, Report Detail, Task Run Detail.
5. Deep domain components: chart panels, research notebooks, import review, assistant, recommendations, hot sectors, market depth.

Each migrated page should keep its current data loading and mutation behavior.

## Data And State Contracts

- Server-rendered data remains the default for page-level payloads.
- URL query state remains the default for filters such as instrument search, report filters, task status, and selected portfolio.
- Server Actions and route proxies remain the mutation path.
- Existing localStorage chart workspace contract must not be expanded into account sync or market-data persistence.
- Existing market color setting continues to govern movement color conventions.

## Accessibility And Responsive Design

- Tables must remain semantic tables, not div grids, when data is tabular.
- Icon-only actions require accessible names.
- Use focus-visible states from primitives; do not remove rings.
- Long labels and translated Chinese text must wrap or truncate intentionally without overlapping controls.
- Mobile layouts may reduce secondary metrics, but must not hide core route actions or create horizontal document overflow.
- Reduced motion users should receive no decorative route/page animation.

## Compatibility And Rollback

- Prefer incremental component/page edits over replacing the whole app shell at once.
- Keep existing tests as behavior guards; add tests when visible behavior changes.
- If token changes make many snapshots/assertions brittle, update assertions around visible behavior rather than implementation classes.
- A rollback can revert individual page migration waves while keeping earlier token/shared-component improvements.

## Trade-Offs

- Chosen direction: professional terminal density improves scan speed and perceived market-product credibility.
- Main cost: the interface can feel intense on mobile and for casual users.
- Mitigation: keep desktop dense, but let mobile/form-heavy views breathe slightly while preserving the same token and component language.
