# State Management

> How state is managed in this project.

---

## Overview

The project does not currently use a global frontend state library or React Query. Most state is either server-rendered data, URL query state, Server Action form state, or small local client component state.

---

## State Categories

- Server data: fetched in server pages using backend helpers, for example `apps/web/app/[locale]/page.tsx` and `apps/web/app/[locale]/task-runs/page.tsx`.
- URL state: filters and selected items use query parameters, for example `status` on the task-runs page and portfolio selection on the portfolios page.
- Mutation state: Server Actions in `apps/web/app/[locale]/actions.ts` mutate backend data and redirect with query-string flash state.
- Local component state: client buttons/forms use `useState`, `useTransition`, or pending flags for loading and user feedback.

---

## When to Use Global State

There is no current global client store. Do not introduce one for isolated page behavior. Consider shared state only if multiple unrelated routes need the same live client-side data and existing server fetch/query state cannot cover it.

---

## Server State

- Prefer server-rendered fetches for page data.
- Use `cache: "no-store"` for task/market data that must reflect backend updates.
- After client mutations, call `router.refresh()` or use Server Actions with `revalidatePath` and `redirect`.

---

## Common Mistakes

- Do not keep backend copies in local state when a server refresh is simpler.
- Do not conflate empty results with failed requests.
- Do not introduce broad global state for a single form or button.

## Scenario: Browser-Local Chart Workspace State

### 1. Scope / Trigger

- Trigger: `AdvancedCandlestickChart` persists a local chart workspace without backend user storage.
- Applies to browser-local research preferences only; do not persist market data in localStorage.

### 2. Signatures

- Storage key: `chart-workspace:v1:{symbol-or-default}`
- UI actions: save workspace, restore workspace, reset workspace.

### 3. Contracts

- `workspaceVersion`: currently `1`
- `selectedRange`: one of the chart range controls such as `1D`, `5D`, `1M`, `3M`, `6M`, `1Y`, `YTD`, or `ALL`
- `visibleIndicators`: MA, BOLL, volume, MACD, RSI, and KDJ boolean flags
- `annotationNote`: research-only text note
- `savedAt`: ISO timestamp string

### 4. Validation & Error Matrix

- Missing key -> show the localized "not found" workspace message.
- Invalid JSON -> ignore the payload and show the same "not found" message.
- Unsupported `workspaceVersion` or `selectedRange` -> ignore the payload.
- Missing indicator flags -> fall back per flag to current default visibility.
- localStorage write/remove failure -> show localized failure or reset status without crashing.

### 5. Good / Base / Bad Cases

- Good: save and restore current range, indicator toggles, and research annotation for the same symbol in the current browser.
- Base: reset removes the local key and restores default chart state.
- Bad: treating localStorage as account sync, server truth, alert state, trading instruction, or persisted market data.

### 6. Tests Required

- Component tests must cover save/restore, invalid localStorage payloads, reset behavior, and preservation of existing indicator controls.
- Tests must clear `window.localStorage` between cases.

### 7. Wrong vs Correct

Wrong:

```typescript
window.localStorage.setItem("chart-layout", JSON.stringify({ bars: marketBars }));
```

Correct:

```typescript
window.localStorage.setItem(
  `chart-workspace:v1:${symbol}`,
  JSON.stringify({ workspaceVersion: 1, selectedRange, visibleIndicators, annotationNote, savedAt }),
);
```

---

## Examples

- URL filter state: `apps/web/app/[locale]/task-runs/page.tsx`
- Server Actions with redirects: `apps/web/app/[locale]/actions.ts`
- Local pending state: `apps/web/components/generate-daily-report-button.tsx`
- Retry interaction state: `apps/web/components/task-run-actions.tsx`
