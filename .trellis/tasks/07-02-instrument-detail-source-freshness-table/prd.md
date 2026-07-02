# Instrument detail source freshness table

## Goal

Turn the instrument detail page into a trustworthy single-symbol market-data workstation by making source, provider, freshness, bar count, and recent OHLCV data visible.

## Requirements

- Strengthen instrument detail market-data display:
  - Show latest daily-bar timestamp/as-of, close, source, provider, and freshness prominently.
  - Display daily bar count and date range for the charted data.
  - Add a compact recent OHLCV table so users can inspect raw daily bars, not just a chart.
- Improve chart/product copy:
  - Avoid wording that implies true real-time quotes.
  - Localize chart empty/loading/error labels where currently hardcoded.
- Error and empty states:
  - Use project `EmptyState`/`ErrorState` patterns.
  - If no bars exist, guide users toward ingestion/provider settings/task-run diagnostics.
- Preserve existing detail-page value:
  - Do not remove reports, indicators, fundamentals, or news sections.
  - Keep links to report generation/detail flows intact.

## Acceptance Criteria

- [ ] Instrument detail displays source/provider/as-of/freshness for daily-bar data.
- [ ] Instrument detail includes a recent OHLCV table with localized labels.
- [ ] Chart and empty-state copy does not claim true real-time support.
- [ ] Empty and failed market-data states are distinct and actionable.
- [ ] Existing report/indicator/fundamental/news sections continue to render.
- [ ] Colocated frontend tests cover source/freshness display and OHLCV rendering.

## Suggested Validation

```powershell
npm run test:web -- "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx"
```

## Notes

- This task is primarily frontend-facing and should reuse existing backend payloads where possible.
- If a required source/provider field is missing from backend responses, document and scope a minimal backend addition.
