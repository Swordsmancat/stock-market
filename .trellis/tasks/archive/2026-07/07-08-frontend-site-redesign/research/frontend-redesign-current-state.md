# Research: Frontend Redesign Current State

Date: 2026-07-08
Task: `07-08-frontend-site-redesign`

## Repository Evidence

- Frontend stack: Next.js App Router under `apps/web`; project specs document Server Components, Server Actions, route handlers, `next-intl`, shadcn-style primitives, and Vitest/Testing Library at `.trellis/spec/frontend/index.md:9-20`.
- Root scripts expose `dev:web` and `test:web`, and dependencies include `next`, `next-intl`, `next-themes`, `lightweight-charts`, `recharts`, `lucide-react`, Tailwind, and Vitest at `package.json:4-5` and `package.json:18-43`.
- Localized app shell wires `TopNavBar`, `SidebarNavigation`, `MobileNavigation`, `Breadcrumbs`, and `BackendStatusBanner`; the main scroll area is defined at `apps/web/app/[locale]/layout.tsx:54-64`.
- Navigation includes ten top-level routes: dashboard, instruments, AI research, evidence, watchlist, portfolios, reports, alerts, task runs, and settings at `apps/web/components/navigation-items.ts:5-51`.
- English and Chinese nav labels are present at `apps/web/messages/en.json:3-12` and `apps/web/messages/zh.json:3-12`.
- Current global tokens are close to default shadcn slate variables, with core HSL variables and radius in `apps/web/app/globals.css:7-49`; Tailwind maps these variables in `apps/web/tailwind.config.ts:4-56`.
- `FinancialPageHeader` exists as a dense finance page header with badges, title, actions, and metrics at `apps/web/components/financial-page-header.tsx:37-49`.
- Current usage of `FinancialPageHeader` is partial: Watchlist at `apps/web/app/[locale]/watchlist/page.tsx:121`, Settings at `apps/web/app/[locale]/settings/page.tsx:33`, and Instrument Detail at `apps/web/components/instrument-detail-client.tsx:154`.
- Several core pages still use ordinary H1/table/card structure rather than the shared finance header: Task Runs at `apps/web/app/[locale]/task-runs/page.tsx:85`, Reports at `apps/web/app/[locale]/reports/page.tsx:147`, Alerts at `apps/web/app/[locale]/alerts/page.tsx:49`, Portfolios at `apps/web/app/[locale]/portfolios/page.tsx:153`, Evidence at `apps/web/app/[locale]/evidence/page.tsx:1178` and `apps/web/app/[locale]/evidence/page.tsx:1227`, Instruments at `apps/web/app/[locale]/instruments/page.tsx:266` and `apps/web/app/[locale]/instruments/page.tsx:304`.
- Table-heavy pages already use shadcn table primitives, for example Watchlist at `apps/web/app/[locale]/watchlist/page.tsx:138-154`, Instruments at `apps/web/app/[locale]/instruments/page.tsx:405-415`, Reports at `apps/web/app/[locale]/reports/page.tsx:211-226`, Alerts at `apps/web/app/[locale]/alerts/page.tsx:59-73`, Portfolios at `apps/web/app/[locale]/portfolios/page.tsx:249-267`, and Task Runs at `apps/web/app/[locale]/task-runs/page.tsx:109-132`.

## Spec Constraints

- Keep user-visible strings in `apps/web/messages/en.json` and `apps/web/messages/zh.json`; update colocated Vitest page tests when rendering behavior changes, per `.trellis/spec/frontend/index.md:19-20`.
- Use `EmptyState` and `ErrorState` for empty/failed-load branches; avoid hardcoded UI strings outside message files, per `.trellis/spec/frontend/component-guidelines.md:18` and `.trellis/spec/frontend/component-guidelines.md:95-96`.
- Core finance pages that need identity plus scan-first KPIs should use `FinancialPageHeader`, per `.trellis/spec/frontend/component-guidelines.md:60-69`.
- Run `npm run test:web` after frontend behavior changes; keep English and Chinese messages synchronized, per `.trellis/spec/frontend/quality-guidelines.md:15-17`.
- Keep page data server-rendered where practical and avoid broad global state for isolated UI behavior, per `.trellis/spec/frontend/state-management.md:9-32`.
- Known type debt includes dynamic `as any` route casts; do not spread more local casts without need, per `.trellis/spec/frontend/type-safety.md:38-42`.

## UI/UX Skill Research

- Generated design system stored at `research/ui-ux-pro-max/design-system/stock-analysis-platform/MASTER.md`.
- The generated system categorizes the app as `Financial Dashboard`, recommends balanced modern variance, standard motion, and dense dashboard density at `MASTER.md:11-12`.
- It recommends `Data-Dense Dashboard` for financial analytics and enterprise reporting at `MASTER.md:164`.
- Its pre-delivery checklist emphasizes no emoji icons, visible focus states, reduced motion, responsive breakpoints, no hidden fixed-nav content, and no mobile horizontal scroll at `MASTER.md:214-227`.
- Additional stack research supports App Router, Server Components by default, dynamic imports for heavy components, and server-side data fetching for initial data.
- Additional shadcn research supports semantic components, shadcn `Table` for structured data, and proper table header/body/cell structure.
- Additional UX research emphasizes skeleton/loading feedback, 150-300ms interaction timing, z-index scale discipline, and lazy loading where appropriate.
- Additional chart research recommends line charts for time-series, candlesticks for OHLC data, streaming charts only with pause/reduced-motion support, and data-table fallbacks for accessibility.

## Prior Task Boundary

- Archived `07-03-frontend-ui-polish` completed earlier UI polish, color-scheme, screenshot, and WCAG evidence work.
- Active `07-03-professional-financial-dashboard` tracks deeper professional-terminal parity: production data/provider validation, Level-2/order-flow/fund-flow, screeners, backtests, configurable workstations, portfolio/risk analytics, and richer research corpus.
- This new task should not duplicate terminal feature work. Its value is a whole-site front-end system pass over existing routes and components.
