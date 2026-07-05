# Professional Chart Workspace Enhancements - Implementation Plan

## Execution Order

1. Re-read the chart component, chart helper tests, instrument-detail usage, i18n messages, and documentation immediately before editing.
2. Confirm existing chart props and indicator state so new workspace state stays additive.
3. Add a small, typed chart workspace model in the frontend layer only.
4. Add defensive localStorage read/write helpers for a versioned workspace key.
5. Add UI affordances to save, restore, and reset a single local workspace preset without changing the existing default chart behavior.
6. Add lightweight annotation support, preferably horizontal research levels or chart notes, without implementing full canvas drawing tools.
7. Keep user-visible strings in `apps/web/messages/en.json` and `apps/web/messages/zh.json`.
8. Add focused component tests for:
   - preserving existing indicator toggles;
   - saving and restoring a workspace preset;
   - ignoring invalid localStorage data;
   - rendering annotations as research notes.
9. Update user and developer documentation with persistence and alert/drawing boundaries.
10. Run focused frontend validation first, then broader web tests if practical.
11. Record remaining professional chart gaps as follow-up notes rather than expanding scope mid-task.

## Files To Inspect Before Editing

- `apps/web/components/advanced-candlestick-chart.tsx`
- `apps/web/components/advanced-candlestick-chart.test.tsx`
- `apps/web/lib/chart-indicators.ts`
- `apps/web/app/[locale]/instruments/[symbol]/page.tsx`
- `apps/web/messages/en.json`
- `apps/web/messages/zh.json`
- `docs/manual/user-guide.md`
- `docs/runbooks/developer-maintenance.md`

## First Slice Checklist

- [x] Identify current chart range and indicator toggle state names.
- [x] Add a versioned workspace state type.
- [x] Add localStorage load/save/reset helpers with validation.
- [x] Add save/restore/reset controls to the chart workspace UI.
- [x] Add a simple annotation/note affordance that is clearly research-only.
- [x] Preserve existing chart rendering, empty state, dark mode, and responsive layout.
- [x] Add or update focused tests for workspace persistence and invalid persisted state.
- [x] Update docs with local-only persistence and non-trading alert boundaries.

## Completed Implementation Notes

- Added browser-local `chart-workspace:v1:{symbol}` storage for selected range, visible indicators, research annotation, and saved timestamp.
- Added save, restore, and reset controls to `AdvancedCandlestickChart` without changing the OHLCV input contract.
- Added defensive parsing so invalid localStorage payloads are ignored and reported as missing workspaces.
- Added focused tests for save/restore, invalid localStorage, reset behavior, and existing indicator controls.
- Updated user and maintainer docs with local-only persistence, research-note semantics, and remaining professional chart gaps.

## Completed Validation

- `npm run test:web -- apps/web/components/advanced-candlestick-chart.test.tsx` -> `9 passed`
- `npm run test:web` -> `29 passed`, `101 passed`

## Deferred Follow-ups

- Full pointer-based trendlines and drawing tools.
- Server-side multi-device layout synchronization.
- User authentication and per-account chart layouts.
- Real multi-timeframe data fetching from inside the chart workspace.
- Chart-linked alert backend workflows if existing alert APIs are insufficient.
- PineScript-style custom formula language.

## Validation Commands

Start with focused chart tests:

```powershell
npm run test:web -- apps/web/components/advanced-candlestick-chart.test.tsx
```

Run related instrument-detail tests if the chart props or page usage changes:

```powershell
npm run test:web -- apps/web/app/[locale]/instruments/[symbol]/page.test.tsx
```

Run broader web regression when practical:

```powershell
npm run test:web
```

## Rollback Points

- After adding localStorage helpers and tests.
- After adding UI controls and focused tests.
- After documentation updates.

## Out-Of-Scope Unless Explicitly Approved

- Backend schema migrations for layouts.
- Real trading/order placement integration.
- Full TradingView parity.
- Large charting-library replacement.

## Completed Implementation Notes

- Added `ChartWorkspacePreset` with schema version `1` and a `chart-workspace:v1:{symbol}` localStorage key.
- Save/restore/reset actions now preserve selected range, indicator visibility, and a lightweight research annotation.
- Invalid or incompatible localStorage values are ignored and surfaced as a safe "not found" restore state.
- The chart keeps existing MA/BOLL/volume/MACD/RSI/KDJ behavior and existing range controls.
- Documentation clarifies that local workspace state is browser-local and chart notes/alerts are research workflow aids, not trading instructions.

## Completed Validation

- `npm run test:web -- apps/web/components/advanced-candlestick-chart.test.tsx` -> `9 passed`
