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

---

## Examples

- URL filter state: `apps/web/app/[locale]/task-runs/page.tsx`
- Server Actions with redirects: `apps/web/app/[locale]/actions.ts`
- Local pending state: `apps/web/components/generate-daily-report-button.tsx`
- Retry interaction state: `apps/web/components/task-run-actions.tsx`
