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

`TopNavBar` is a server component. It passes the resolved locale plus a
serializable `labels` object to `GlobalSearch`, and a serializable `labels`
object to `NotificationBell`. These client islands must not independently
re-resolve translated shell copy; their browser-only responsibility is
interaction and bounded client fetching.

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

**Provider status ownership contract**: Provider names, priorities,
configuration state, credential readiness, and implementation status belong to
Settings. The homepage may read
`getPlatformSettings().news_search_provider_capabilities` only as an input to
the aggregate AI sentiment/data-health summary; it must not render a separate
provider status panel or provider-level operational details. Public settings
must continue to redact `news_search_provider_keys`.

**Citation boundary**: Provider capability data used by the homepage is an
aggregate readiness input only. Search results become citable evidence only
after they are stored locally as `NewsArticle` rows or another approved local
evidence record.

**Stored-news time contract**: Format homepage `published_at` values with the
active locale and explicit `timeZone: "Asia/Shanghai"`; server or container
defaults must not change the displayed date. Render the valid value in a
semantic `<time dateTime={published_at}>` before truncatable source/confidence
metadata. Missing or invalid values use the existing unavailable label.

**Module action contract**: Every visible homepage terminal module should expose a localized "More" link to the owning routed module. Use real `Link` navigation, not click handlers, and keep action text in `apps/web/messages/en.json` and `apps/web/messages/zh.json`. If a module has a second setup action, such as adding a macro indicator, render it next to "More" inside the existing panel action area.

**Fixed panel layout contract**: Fixed-height homepage panels should keep the card as `flex flex-col`, the content area as `min-h-0 flex-1`, and the table/list body as `min-h-0 flex-1 overflow-y-auto`. Headers should be `shrink-0`; rows should truncate or line-clamp rather than resizing the panel. This keeps the dashboard stable at desktop and tall mobile visual-check sizes.

The six homepage terminal modules use two columns and three natural rows at the
`xl` breakpoint, and one column below it. Do not stretch fixed-height chart
cards to fill a viewport gap; that only moves unused space inside the charts.
At narrow widths, prioritize the indicator name and value, then place secondary
status/date metadata below the name. Keep the bounded body as a named,
focusable scroll region.

**Homepage read budget contract**: Server-rendered homepage reads remain GET
only and use named timeout budgets based on observed latency. Lightweight
optional reads keep the five-second budget. The cold
`/dashboard/market-overview` aggregation has a dedicated twenty-second budget.
Do not reuse the lightweight timeout for that aggregation, and do not turn a
longer read budget into a refresh, ingestion, backfill, or observation write.
Abort and non-2xx responses retain the explicit unavailable state, and timeout
handles must be cleared in `finally`.

**Macro label boundary**: Backend macro `code` and `name` fields are canonical
evidence metadata and remain unchanged. The curated homepage resolves every
known built-in code through symmetric `Dashboard` translation keys; an unknown
code falls back to its stored name, then the code. Do not render raw technical
code subtitles on the homepage. Test both loaded and failed overview
projections because the failed projection has only configured codes and no
stored names to fall back to.

When a fixed panel body can overflow, make the scroll owner a focusable named
region: reuse the panel heading through `aria-labelledby`, set `tabIndex={0}`,
and retain a visible `focus-visible` ring. Render every row already inside the
panel's bounded input rather than hiding later rows before scrolling. Apply
`overscroll-contain` only at the breakpoint where height is constrained; an
unconstrained mobile panel must continue passing wheel/touch movement to the
page. A page regression should inject enough rows to reach the last item and
assert that item inside the named region. Browser acceptance should confirm
`overflowY === "auto"`, `scrollHeight > clientHeight`, and a real wheel action
changes `scrollTop` at the constrained desktop breakpoint.

**Example**:

```tsx
const providers = platformSettings.news_search_provider_capabilities ?? [];
const summary = buildAiSentimentSummary({
  newsItems,
  healthCounts,
  checkedInstrumentCount,
  sectors,
  providers,
});

<AiSentimentPanel summary={summary} t={t} />
```

Homepage tests should assert that provider names and the provider status heading
remain absent even when capability fixtures contain configured and degraded
providers. Settings page tests own provider-level configuration/status
coverage. They should also prove capability data still changes aggregate
provider readiness, and use a cross-midnight UTC news timestamp to lock the
Shanghai display date and metadata order. Homepage tests should also assert the
"More" hrefs and any setup action hrefs for modules that add them.

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

### Convention: Bounded Technical Indicator Summaries

**What**: Scalar technical indicators may use the generic compact formatter. Known
object-valued indicators must render a field-specific summary and may expose only
a bounded whitelist of secondary fields through a native `<details>` element.
Never render raw bucket arrays or stringify the complete object into the default
instrument-detail view.

**Why**: Stored indicator payloads can contain dozens of nested price buckets.
Rendering the payload generically hides the decision-relevant values, creates
unbounded page height, and makes the detail page difficult to scan on mobile.

**Example**:

```tsx
if (code === "chip_distribution") {
  return (
    <>
      <IndicatorSummaryMetric label={labels.averageCost} value={averageCost} />
      <details>
        <summary>{labels.moreDetails}</summary>
        <BoundedIndicatorMetadata topBuckets={topBuckets.slice(0, 5)} />
      </details>
    </>
  );
}
```

Preserve numeric zero as a valid value, render null or invalid numbers with the
localized unavailable label, keep disclosures closed by default, and give their
summary a visible keyboard focus state. Component tests must assert key summary
values, truthful empty states, bounded disclosure controls, and the absence of
raw payload field names such as `cumulative_share`.

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
