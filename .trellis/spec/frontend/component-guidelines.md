# Component Guidelines

> How components are built in this project.

---

## Overview

The frontend uses server-rendered pages for data-heavy screens and small client components for browser interactions. Shared UI primitives live under `apps/web/components/ui`, while domain interaction components live directly under `apps/web/components`.

---

## Component Structure

- Server pages fetch data before rendering, as in `apps/web/app/[locale]/task-runs/page.tsx` and `apps/web/app/[locale]/reports/page.tsx`.
- Client components start with `"use client"`, keep local pending/message state, and call route proxies or Server Actions. Examples: `apps/web/components/task-run-actions.tsx` and `apps/web/components/generate-daily-report-button.tsx`.
- Prefer composition with existing UI primitives such as `Card`, `Table`, `Badge`, and `Button`.
- Use `EmptyState` and `ErrorState` for empty and failed-load branches instead of ad-hoc text blocks.

---

## Props Conventions

- Define a `Props` type near the component.
- Use descriptive prop names such as `taskRunId`, `symbol`, `start`, and `end`.
- Keep component props serializable when the component is used from a server page.
- Use union types for variants when following existing UI primitives, as in `GenerateDailyReportButton`.

### Convention: Localized Labels For Server-Rendered Client Components

**What**: When a server page renders a client component that needs localized shell text, pass a serializable `labels` object of translated strings from the server page instead of passing formatter functions or hardcoding one language inside the client component.

**Why**: Server-to-client props must remain serializable, and isolated component tests should not need a full `next-intl` provider just to verify rendering. This also prevents English pages from showing Chinese-only component chrome while preserving backend-provided data such as recommendation titles and reasons.

**Example**:

```tsx
<SmartRecommendations
  locale={locale}
  recommendations={items}
  labels={{
    title: t("smartRecommendationsTitle"),
    description: t("smartRecommendationsDesc", { count: items.length }),
    emptyMessage: t("smartRecommendationsEmpty"),
  }}
/>
```

Do not pass functions such as `description: (count) => t("key", { count })` across the server/client boundary.

---

## Styling Patterns

- Styling is Tailwind class based.
- Prefer existing UI primitives before creating new markup.
- Use layout utility classes directly in page/component JSX, following existing pages.
- Keep class names readable and avoid extracting one-off class constants unless they are reused.

### Convention: Dense Financial Page Headers

**What**: For core finance pages that need page identity plus scan-first KPIs, use `FinancialPageHeader` from `apps/web/components/financial-page-header.tsx`.

**Why**: Dashboard, watchlist, instrument detail, and settings pages should share the same compact terminal-style header instead of each page recreating a decorative hero or loose title block. This keeps financial UI dense, consistent, and testable.

**Example**:

```tsx
<FinancialPageHeader
  title={t("title")}
  description={t("description")}
  badges={[{ label: t("activeProvider", { provider }) }]}
  metrics={[
    { label: t("latestPriceCard"), value: currentPrice.toFixed(2) },
    { label: t("priceChange"), value: formattedChange, className: getMovementColor(change) },
  ]}
  actions={<Button size="sm">{t("save")}</Button>}
/>
```

If a badge intentionally repeats the title text, tests should target the semantic heading with `getByRole("heading", { name })` instead of assuming a unique text node.

### Convention: Curated Dashboard Homepage

**What**: The dashboard homepage is a curated market overview, not a full research workspace. Keep it limited to the top index ticker, core US/A-share index cards, macro favorites, hot sectors, latest news sentiment, and compact important status. Put AI research briefs, source-readiness workflows, recommendations, comparison tools, K-line workspaces, reports, technical indicators, and fundamentals in their routed modules.

**Why**: The homepage is the scan-first entry point. Expanding every feature there makes the product harder to read and duplicates ownership from AI Research, Macro Research, Instruments, Reports, Alerts, and Task Runs.

**Example**:

```tsx
<MarketTicker items={tickerItems} labels={tickerLabels} />
<FinancialDashboardHero title={t("homeOverviewTitle")} metrics={homepageMetrics} />
<HotSectors sectors={hotSectorItemsForHome} />
```

Use page tests to assert both sides of the contract: the curated market sections render, and deep modules such as `AI research brief`, `Followed K-line charts`, `Daily Report`, and `Technical Indicators` do not render on the homepage. When moving a deep module off the homepage, also add or update the owning submodule test so the feature is still visible in its routed home, for example AI workflows under AI Research, comparison/K-line workflows under Instruments, and reports or report history under Reports or Instrument Detail.

### Convention: Terminal Dashboard Homepage

**What**: The homepage is the first-run terminal dashboard. Keep the app's first-run theme default set to dark, keep the top ticker and homepage panels dense, and use compact tables/cards with lightweight SVG sparklines or status bars when existing payloads already contain the data.

**Why**: The homepage should match the product's market-terminal direction without turning into a marketing page or duplicating deep research workflows.

**Provider strip contract**: The homepage news/provider status strip reads from `getPlatformSettings().news_search_provider_capabilities`. It may display `display_name`, `enabled`, `configured`, `credential_required`, `credential_configured`, `implementation_status`, and `priority`. It must not expose `news_search_provider_keys`; public settings already redact key values.

**Citation boundary**: News search providers on the homepage are readiness/status signals only. Search results become citable evidence only after they are stored locally as `NewsArticle` rows or another approved local evidence record.

**Module action contract**: Every visible homepage terminal module should expose a localized "More" link to the owning routed module. Use real `Link` navigation, not click handlers, and keep action text in `apps/web/messages/en.json` and `apps/web/messages/zh.json`. If a module has a second setup action, such as adding a macro indicator, render it next to "More" inside the existing panel action area.

**Fixed panel layout contract**: Fixed-height homepage panels should keep the card as `flex flex-col`, the content area as `min-h-0 flex-1`, and the table/list body as `min-h-0 flex-1 overflow-y-auto`. Headers should be `shrink-0`; rows should truncate or line-clamp rather than resizing the panel. This keeps the dashboard stable at desktop and tall mobile visual-check sizes.

**Example**:

```tsx
const newsSearchProviderCapabilities =
  platformSettings.news_search_provider_capabilities ?? [];

<NewsProviderStrip providers={newsSearchProviderCapabilities} />
```

Tests should assert that the provider strip renders at least one configured provider and one setup/degraded state when the fixture includes both. Homepage tests should also assert the "More" hrefs and any setup action hrefs for modules that add them.

### Convention: Terminal Entry Page Sections

**What**: Routed pages opened from homepage terminal module actions should keep `FinancialPageHeader` for the top summary and use `FinancialTerminalCard`, `FinancialTerminalCardHeader`, `FinancialTerminalCardContent`, and `FinancialTerminalSurface` from `apps/web/components/financial-terminal-section.tsx` for downstream sections.

**Why**: Homepage "More" destinations should feel like the same market terminal without changing the global `Card` primitive or duplicating long Tailwind strings across instruments, evidence, settings, and AI research surfaces.

**Example**:

```tsx
import {
  FinancialTerminalCard,
  FinancialTerminalCardContent,
  FinancialTerminalCardHeader,
  FinancialTerminalSurface,
} from "@/components/financial-terminal-section";

<FinancialTerminalCard>
  <FinancialTerminalCardHeader>
    <CardTitle>{t("tableTitle")}</CardTitle>
    <CardDescription>{t("tableDescription")}</CardDescription>
  </FinancialTerminalCardHeader>
  <FinancialTerminalCardContent className="p-0">
    <div className="overflow-x-auto">
      <Table>{/* rows */}</Table>
    </div>
  </FinancialTerminalCardContent>
</FinancialTerminalCard>
```

Use `FinancialTerminalSurface` for nested metric tiles, source rows, diagnostics, or preview blocks. Keep numeric values in `font-mono` where they are scan-first data. If the change only touches visual classes and no visible behavior changes, keep tests focused on existing route actions, headings, forms, empty/error states, and run Chrome visual checks at desktop and tall mobile sizes.

### Convention: Personal Research Core Before Maintenance

**What**: Keep repeated personal research actions and independently loaded
read-only evidence directly visible. Put provider refreshes, backfills, bulk
ingestion, raw status, and other mutation-heavy operations in native
`<details>` elements that are closed by default. The primary navigation is
limited to Home, AI Research, Instruments, Watchlist, and Settings; hidden
routes remain directly addressable and their services/data are not deleted.

**Why**: This installation is a personal research workspace. Operational
controls must remain available without dominating candidate review, cited
analysis, watchlist use, or saved evidence. A failure in one aggregate request
must not hide notes, briefs, disclosures, or other independently loaded data.

**Example**:

```tsx
<ReadOnlyEvidence payload={loadedEvidence} />
<details>
  <summary>{labels.maintenanceSummary}</summary>
  <RefreshAndIngestionActions />
</details>
```

Do not place read-only evidence inside the maintenance disclosure merely
because the same component also owns refresh actions. Keep the protected
homepage page source and its main content unchanged when simplifying the shared
shell. Tests should assert core/maintenance DOM ownership, the missing `open`
attribute, mixed-success rendering, five-item responsive navigation, and no
horizontal page overflow.

---

## Accessibility

- Use real buttons for actions and links for navigation.
- Keep visible button text translated and assertable in tests, for example the retry button in `task-run-actions.tsx`.
- Table empty/error rows should set `colSpan` to cover all visible columns.

### Convention: Immutable Snapshot Locale Boundary

**What**: Persisted research snapshots keep their generation locale as
provenance. Localize current-page UI from structured codes and fields. Do not
render backend free-text readiness, diagnostic, gap, invalidation, factor, or
safety messages as UI copy. When immutable explanation prose was generated in
another locale, show a localized provenance notice instead of the raw prose.

**Why**: Locale is intentionally excluded from daily cohort identity. Reusing
one immutable run across English and Chinese pages must not create duplicate
cohorts or leak the first request's language into later UI.

**Example**:

```tsx
const sameLocale = normalizeLocale(run.locale) === normalizeLocale(locale);

return sameLocale
  ? <PublishedExplanation>{run.explanation_markdown}</PublishedExplanation>
  : <LocaleProvenanceNotice locale={run.locale} />;
```

Use exhaustive mappings for known structured codes and a localized unknown-code
fallback. The complete cross-layer contract is in
`../backend/daily-research-shortlist-contract.md`.

---

## Common Mistakes

- Do not silently render an empty state when the backend request failed; use `ErrorState`.
- Do not add user-visible hardcoded strings outside `apps/web/messages/*.json`.
- Do not duplicate interaction logic when an existing component already covers the flow.
- When a server page passes a translated template string to a client component that later performs manual `.replace("{name}", value)` formatting, do not call `t("key")` on a message containing placeholders. Pass placeholder literals through the translator, for example `t("selectedFile", { name: "{name}" })`, or the real `next-intl` runtime may render the raw namespace key such as `ResearchSourceNotebook.completenessSummary`.

## Scenario: Official Disclosure Evidence Operations Panel

- `apps/web/app/[locale]/evidence/page.tsx` server-loads watchlist disclosure coverage and passes serializable localized labels to `OfficialDisclosureEvidencePanel`.
- The client panel calls only same-origin proxies for one exact disclosure, one bounded watchlist batch, or one incremental monitor run, then uses `router.refresh()`.
- Metadata-only and extracted-section evidence boundaries must remain visible. Empty and failed-load states are distinct.
- Monitoring renders backend-owned `fresh`, `stale`, `backoff`, and `never` projections plus last-run new counts. It must not derive a second cursor/SLA model or turn new disclosures into automatic investment conclusions.
- Batch/monitor success exposes the existing TaskRun detail link; the panel does not poll or implement a second job-state model.
- Component, page, and route-proxy tests cover rendering, request identity, task links, error state, and both locale catalogs.
