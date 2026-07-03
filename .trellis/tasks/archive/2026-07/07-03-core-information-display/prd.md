# Improve core information display

## Goal

Make the product's most important stock-market information obvious at a glance. Users should not have to infer whether data exists, whether it is fresh, which provider produced it, what changed recently, or what action to take next.

## User value

- A user opening the app can immediately understand the current market-data state.
- A user viewing an instrument can immediately see price, change, volume, freshness, data source, and next actions.
- A user viewing reports can quickly scan generated insights instead of reading opaque markdown previews.
- Empty or failed data states explain the next useful action instead of looking like unfinished UI.

## Confirmed facts from repository inspection

- The dashboard page (`apps/web/app/[locale]/page.tsx`) already fetches many datasets: instruments, latest bar, recent bars, reports, portfolio, indicators, fundamentals, news, latest task run, watchlist, and alerts.
- The dashboard currently spreads information across KPI cards and secondary cards, but it does not provide a unified "what matters now" summary for data availability, freshness, latest move, provider, and next action.
- The instruments page (`apps/web/app/[locale]/instruments/page.tsx`) already lists instruments with latest close, as-of date, source/provider, freshness, and actions, but the table is still mostly an inventory view rather than a decision dashboard.
- The instrument detail page (`apps/web/app/[locale]/instruments/[symbol]/page.tsx`) already displays daily bars, freshness, source/provider, chart, OHLCV table, indicators, fundamentals, news, and report content, but the top of the page needs a stronger priority hierarchy for the latest daily move and data health.
- The reports page (`apps/web/app/[locale]/reports/page.tsx`) lists reports and task-run links, but previews are simple markdown snippets rather than an insight-first summary.
- Frontend guidelines require server-rendered data-heavy pages, shared UI primitives, localized strings in both `en.json` and `zh.json`, and focused Vitest coverage for changed page behavior.

## Problem statement

The project has acquired the necessary data-display plumbing, but the presentation still feels like a collection of raw panels. The next step is to turn it into an information product: the highest-value information must be prioritized, grouped, and explained before secondary details.

## Requirements

## Prioritization decision

This task will prioritize the dashboard as the primary information command center, then improve the instrument detail first screen, with necessary supporting enhancements on the instruments list and reports page.

Rationale: the dashboard is the user's default entry point and should first answer whether market data exists, whether it is fresh, which provider produced it, what changed, and what action to take next. Instrument detail should then provide the deeper single-symbol story. Instruments and reports should support scanning and follow-up without becoming the center of this first redesign.

The dashboard's primary subject is data health plus watchlist overview. A single primary instrument remains useful as a default focus target, especially when no watchlist is configured, but it should not make the dashboard feel like a one-symbol detail page. Portfolio performance is not the dashboard's primary subject in this iteration because the current portfolio data is demo-oriented and could mislead users if promoted too strongly.

When data is stale, missing, or unavailable, the UI should prioritize a clear primary action before diagnostics. The primary action should be one-click ingestion or refresh when available. Diagnostics such as task-run history, provider settings, and failure context should remain visible as secondary links so users can resolve provider or task issues without losing the main path forward.

The dashboard may be strongly reorganized in this iteration. The first screen should become a focused data-health workspace instead of preserving the current equal-weight card grid. Demo-oriented or secondary panels such as portfolio, news, fundamentals, and long report previews may be demoted below the fold when they compete with market-data readiness and watchlist visibility.

Daily price movement should use neutral, text-first semantics in this iteration. Direction must be explicit through signs, arrows, and localized labels such as up/down or rising/falling. Color may be used as a subtle secondary cue, but the UI must not rely on red/green alone because US/global and Chinese market color conventions conflict.

Dashboard data-health counts should use a watchlist-first scope. When the user has watchlist entries, the health summary should describe those watched instruments. When the watchlist is empty, the dashboard should use a bounded default sample of the first 25 instruments, matching the current frontend performance pattern. The UI must label this honestly as a watchlist or default-sample summary, not as a whole-market statistic.

### R1. Dashboard must become a market-data command center

- Show an at-a-glance data status summary near the top: instrument count, primary symbol, latest daily close, latest daily change when available, latest bar date, freshness, source, and provider.
- Treat data health and watchlist status as the primary dashboard story, with the primary instrument as a fallback focus item.
- Calculate dashboard data-health counts from the watchlist when available; otherwise use the first 25 instruments as a default sample and label the scope clearly.
- Highlight the most important next action based on state: ingest data, refresh stale data, inspect latest task run, adjust provider settings, or open the primary instrument.
- Present ingestion or refresh as the primary CTA for missing/stale market data, with task-run and settings diagnostics as secondary links.
- Reorganize the first screen around data-health status, watchlist overview, primary instrument daily story, provider, latest task status, and the main next action.
- Demote demo-oriented or secondary panels below the primary dashboard workspace when they distract from data availability and freshness.
- Keep existing ingestion and analysis actions available, but place them in the context of data readiness instead of as isolated buttons.

### R2. Instruments page must prioritize scannable market state

- Preserve search/filter functionality.
- Add a summary layer above the table that explains how many visible instruments have fresh, stale, missing, or unavailable latest daily data.
- Make row-level status easier to scan, including latest close, as-of date, freshness, and source/provider.
- Keep detail/report/task-run navigation clear.

### R3. Instrument detail must lead with the latest daily story

- The first screen should emphasize latest close, daily change, percentage change, volume, date, freshness, source/provider, and data range.
- Daily change direction must be readable from text/signs/labels without relying on red/green color semantics.
- Chart and OHLCV details should remain available but should not bury the current state summary.
- No-data and failed-load states should explain why the page cannot show the latest story, prioritize ingestion/refresh when available, and point users to settings/task-run diagnostics as secondary follow-up.

### R4. Reports page must become insight-first

- Make generated reports easier to scan by surfacing report type, symbol, as-of date, task-run link, and a cleaner preview.
- If report content has a recognizable first heading or summary line, show that as the primary preview rather than an arbitrary markdown substring.
- Keep full-report navigation and generation actions.

### R5. Messaging and localization

- All user-visible copy must be localized in English and Simplified Chinese.
- Copy must be honest that the current supported market data is latest daily bar / historical daily data, not true real-time quotes.

### R6. Quality and regression coverage

- Add or update focused frontend tests for dashboard, instruments, instrument detail, and reports behavior changed by this task.
- Tests should verify visible summaries, links/actions, empty states, and failed-data messaging where applicable.

## Acceptance Criteria

- [ ] Dashboard top section answers: "What data do I have, how fresh is it, and what should I do next?"
- [ ] Dashboard data-health summary clearly labels whether it describes the watchlist or the default instrument sample.
- [ ] Instruments page includes a visible data-health summary for fresh/stale/no-data/unavailable latest daily bars.
- [ ] Instrument detail top section includes latest close plus daily absolute/percentage change when at least two daily bars exist.
- [ ] Daily price movement uses explicit signs/labels and does not rely on red/green alone.
- [ ] Instrument detail top section includes latest volume, latest bar date, freshness, source, provider, and chart range.
- [ ] No-data and failed-load states on display pages provide actionable next steps rather than only empty tables.
- [ ] Reports page previews prioritize a readable insight/heading when possible.
- [ ] English and Chinese message files are updated together.
- [ ] Focused Vitest coverage is updated for changed UI behavior.
- [ ] The task passes Trellis validation and relevant frontend tests.

## Out of scope

- True real-time quote support.
- New provider integrations or backend market-data contracts unless existing fields are insufficient for display.
- Portfolio accounting accuracy improvements.
- Full charting redesign beyond the summary hierarchy around existing charts.
- AI report-generation quality changes beyond surfacing existing report content better.

## Open questions

- None blocking.
