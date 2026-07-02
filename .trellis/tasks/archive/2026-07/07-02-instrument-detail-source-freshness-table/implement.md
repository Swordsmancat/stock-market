# Instrument detail source freshness table - Implementation Plan

## Scope

Improve the existing instrument detail page with source/provider/freshness metadata and a compact OHLCV table. Keep the work frontend-scoped and reuse the existing bars endpoint payload.

## Steps

1. Start the Trellis child task.
2. Update `apps/web/app/[locale]/instruments/[symbol]/page.tsx`.
   - Replace bars fallback loading with a result type that distinguishes failed and loaded states.
   - Add helper functions for formatting latest close, timestamps, counts, provider/source, freshness, and recent OHLCV rows.
   - Add a prominent daily-bar summary card.
   - Add `EmptyState` / `ErrorState` rendering for chart and table branches.
   - Add a recent OHLCV table under the price history card.
3. Update `apps/web/components/price-chart.tsx`.
   - Accept localized chart labels from the page while preserving existing defaults.
4. Update `apps/web/messages/en.json` and `apps/web/messages/zh.json` together.
5. Update `apps/web/app/[locale]/instruments/[symbol]/page.test.tsx`.
   - Cover source/provider/freshness summary.
   - Cover recent OHLCV rendering.
   - Cover no-data or failed bars state.
6. Run focused validation and lint diagnostics.
7. Commit, push, archive the Trellis task, and push the archive commit.

## Validation

```powershell
npm run test:web -- "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx"
python ./.trellis/scripts/task.py validate .trellis/tasks/07-02-instrument-detail-source-freshness-table
```
