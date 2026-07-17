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

### Convention: Macro Evidence vs Market Structure Ownership

**What**: `/evidence` owns macroeconomic and valuation evidence. Economic
release timing and stored industry performance belong to `/market-research`,
which owns the database-only calendar and industry-ranking GET requests and
reuses their existing explicit-refresh panels.

**Why**: An economic release calendar is an event-planning tool and an industry
gain history is market-structure evidence. Rendering or fetching them from
Macro Research blurs module ownership and makes an already dense personal
research page harder to scan.

**Example**:

```tsx
// /market-research
const [calendar, rankings] = await Promise.all([
  fetchEconomicCalendar(),
  fetchIndustryRankings(),
]);

// /evidence keeps a localized link, but performs neither request.
<Link href="/market-research">{t("openMarketResearch")}</Link>
```

Expose Market Research in the desktop sidebar, but keep the five-item personal
mobile navigation stable by marking that shared navigation item desktop-only.
The page also remains reachable through explicit page-header links and
localized breadcrumbs.
When a full monthly calendar contains many rows, retain every row inside a
focusable named internal scroll region with a sticky header so the following
industry panel remains reachable. Page tests must assert both sides of route
ownership: Market Research issues the two GETs, while Macro Research neither
renders the panels nor issues those requests.

### Convention: Independent Instrument Research Streams

**What**: After the live assistant on an instrument detail page, render the
research modules as two independent, top-aligned streams at `xl`: the wider
primary stream contains K-line, intraday, news, and the saved AI report; the
narrower evidence stream contains technical indicators and fundamentals. Below
`xl`, keep those two streams in the same DOM order as one natural page flow.

**Why**: A single short card next to one nested stack inherits the stack's full
grid-row height. That stretched the saved report into thousands of pixels of
empty surface and pushed the charts far below the useful evidence. Independent
streams keep variable-height cards truthful and let personal research content
use both columns without CSS-only reordering.

**Example**:

```tsx
<div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
  <div className="grid min-w-0 content-start gap-4">
    {kline}
    {intraday}
    {news}
    {savedReport}
  </div>
  <div className="grid min-w-0 content-start gap-4">
    {technicalIndicators}
    {fundamentals}
  </div>
</div>
```

Do not use one card as the first grid item and a nested multi-card stack as the
second item. Component tests should assert column ownership and DOM order.
Browser acceptance covers `1280x720` column geometry and `390x844` single-column
order, with no horizontal overflow at either viewport.

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

The instrument detail summary also treats indicator and nested-field labels as
localized UI, not stored evidence text. Keep a bounded map for the API's known
`ma`, `rsi`, `bollinger`, `atr`, `macd`, `kdj`, `cci`, `obv`, `roc`, `bias`,
`mfi`, and `william_r` codes in the `InstrumentDetail` catalog. Map known
Bollinger and MACD object fields to localized labels, retain conventional
uppercase `K`/`D`/`J`, and fall back to the original code or field for anything
unknown. Never drop or reinterpret an unknown value merely to avoid showing its
stored key. Tests render both Chinese and English catalogs and include an
unknown indicator plus unknown nested field.

Candlestick pattern labels follow the same bounded localization contract. Map
the five `candlestick_patterns_v1` codes (`bullish_engulfing`,
`bearish_engulfing`, `doji`, `hammer`, and `shooting_star`) through symmetric
`InstrumentDetail` messages for both structured objects and legacy string
values. For a known structured pattern, the localized code label takes
precedence over a stored English `name`. Unknown structured patterns fall back
to `name`, then `pattern`, then `code`; unknown strings remain unchanged. Keep
the existing five-item summary bound. Tests that cover all known codes and
unknown fallbacks must use separate bounded fixtures rather than requiring more
than five rows in one summary.

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

The AI Research Desk applies that boundary to assistant context as well. Its
active macro summary and default question include only indicators with a value,
`as_of`, and source, because only those rows are citable local observations.
Known macro codes resolve through the shared
`apps/web/lib/macro-indicator-labels.ts` map and `Dashboard` catalog; unknown
codes fall back to stored name, then code. Missing-code lists, provider setup
actions, refresh instructions, and raw diagnostic prose remain available in a
closed source-maintenance `<details>` block but never enter the default model
question. Default macro cards show localized missing-observation copy rather
than backend English no-data reasons. Component and page tests must assert both
the prompt exclusion and the closed maintenance ownership without making an
assistant request.

---

## Accessibility

### Convention: Stored-Evidence Macroeconomic Dashboard

**What**: The Evidence Center begins with a scan-first macroeconomic dashboard grouped into rates, economic fundamentals, valuation, external economy, money supply, and fiscal revenue. Cards show localized names, latest stored value, as-of date, source, change/direction text, and bounded history sparklines. Provider operations and the legacy evidence workspace remain inside a closed maintenance disclosure.

**Why**: Personal research needs broad macro context without making normal page loads slow, mutable, or dependent on provider availability.

**Example**:

```tsx
<MacroEconomicDashboard payload={storedDashboard} labels={localizedLabels} />
<details>
  <summary>{labels.maintenanceSummary}</summary>
  <EvidenceMaintenanceWorkspace />
</details>
```

The component may POST only after the user activates its refresh button. A failed refresh keeps the previously rendered payload visible and adds a localized error. Known indicator codes resolve through `macro-indicator-labels.ts`; missing observations use localized no-data copy rather than raw backend diagnostics. Use text or arrows together with color, keep SVG sparklines accessible, and retain a responsive two/three/four-column grid without horizontal overflow. Component tests cover populated, missing, degraded, and failed-refresh states in both locale catalogs.

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
