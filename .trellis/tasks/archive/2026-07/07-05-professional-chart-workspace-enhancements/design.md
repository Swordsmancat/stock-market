# Professional Chart Workspace Enhancements - Design

## Scope

Upgrade the existing candlestick chart experience toward a professional chart workspace while preserving the current MVP chart behavior. The first implementation slice should be intentionally small and reversible: saved workspace presets and lightweight annotation affordances before larger TradingView-style drawing, scripting, or backend persistence work.

## Current Entry Points

- Chart component: `apps/web/components/advanced-candlestick-chart.tsx`
- Indicator helpers: `apps/web/lib/chart-indicators.ts`
- Instrument detail page: `apps/web/app/[locale]/instruments/[symbol]/page.tsx`
- Chart tests: `apps/web/components/advanced-candlestick-chart.test.tsx`
- i18n messages: `apps/web/messages/en.json`, `apps/web/messages/zh.json`
- User docs: `docs/manual/user-guide.md`
- Maintainer docs: `docs/runbooks/developer-maintenance.md`

## Workspace State Model

The chart workspace state should remain additive to the current chart props and should not change the data contract for OHLCV bars.

Candidate state fields:

- `selectedRange`: the current chart range/time-window selection.
- `enabledIndicators`: MA, BOLL, volume, MACD, RSI, KDJ and future optional indicators.
- `indicatorParameters`: periods and display options when the UI supports them.
- `paneLayout`: main chart plus volume/indicator panes, including collapsed/expanded state.
- `annotationDraft`: current drawing/annotation mode and temporary input.
- `annotations`: persisted user annotations such as horizontal levels, notes, or trendlines.
- `presetName`: user-visible saved preset name.
- `workspaceVersion`: schema version for persisted client state.

## Persistence Boundary

Because the current application does not expose authenticated user storage for chart layouts, the first slice should use browser-local persistence only, with a clearly versioned localStorage schema.

Recommended key shape:

```text
chart-workspace:v1:{symbol-or-scope}
```

Rules:

- Persist only user preferences and annotations, never market data.
- Treat localStorage data as untrusted: validate shape and fall back to defaults when parsing fails.
- Keep saved layouts per chart/symbol when the component has a stable symbol; otherwise use a generic workspace key.
- Do not add backend tables or migrations until user identity and multi-device sync requirements are defined.

## Drawing / Annotation Model

The first implementation slice should avoid complex canvas drawing tools and use lightweight, testable annotations:

- Saved horizontal level annotations with label, price/value, color, and created timestamp.
- Optional text notes attached to the chart workspace.
- Future trendline/drawing-tool support should be a separate task because it requires pointer interaction, coordinate transforms, hit testing, and responsive editing.

The UI should clearly label annotations as research notes, not trading orders.

## Indicator Presets And Layouts

Indicator presets should preserve current MA/BOLL/volume/MACD/RSI/KDJ behavior. The first slice may support:

- Save current indicator visibility as a named preset.
- Restore the preset after reload.
- Reset to defaults.

Future slices can add indicator parameter editing and multi-pane layout persistence.

## Multi-Timeframe / Multi-Pane Boundary

The current chart primarily uses the data already loaded by the instrument detail page. A professional multi-timeframe workspace requires backend/API support for additional ranges and possibly intraday intervals. For this task:

- Do not fetch new market data from inside the chart component unless an existing pattern supports it.
- Persist intended interval or layout preference only if it does not imply unavailable data is present.
- Keep multi-pane behavior limited to current indicator panes unless a clear reusable layout model exists.

## Alert Integration Boundary

Chart-linked alerts should be research notifications only:

- No brokerage execution.
- No order placement language.
- Any alert affordance should integrate with existing watchlist/alert rules or create a Trellis follow-up if backend changes are required.
- Documentation must state that chart annotations and alerts are research workflow aids.

## Frontend Requirements

- Keep all new user-visible strings in `apps/web/messages/en.json` and `apps/web/messages/zh.json`.
- Preserve empty/degraded chart states.
- Keep responsive layout usable on narrow screens.
- Add focused Vitest/Testing Library coverage for persistence, reset behavior, and visible annotations.

## Compatibility

- Existing chart props should remain compatible.
- Existing indicator toggle tests should continue to pass.
- Persisted workspace parsing must be defensive so invalid localStorage data cannot crash rendering.

## Risks

- Drawing tools can grow quickly; keep the first slice small and testable.
- localStorage is browser-local only and should not be documented as account sync.
- Multi-timeframe wording must not imply realtime or missing provider capabilities.
