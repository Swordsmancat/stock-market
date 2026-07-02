# Hook Guidelines

> How hooks are used in this project.

---

## Overview

The project currently uses few custom React hooks. Most data fetching happens in server components or Server Actions. Client components use built-in React hooks for pending state, status messages, and transitions.

---

## Custom Hook Patterns

- Add a custom hook only when stateful browser logic is reused across components.
- Keep one-off interaction state inside the client component, as in `apps/web/components/task-run-actions.tsx`.
- If polling logic is shared, keep it in `apps/web/lib`, following `apps/web/lib/task-run-poll.ts`.

---

## Data Fetching

- Server pages use `backendFetch` or direct backend helpers before rendering.
- Client components call Next.js route proxies such as `/api/task-runs/<id>/retry`.
- Server Actions live in `apps/web/app/[locale]/actions.ts` and use `backendFetch`, `revalidatePath`, and `redirect`.

---

## Naming Conventions

- React hook names must start with `use`.
- Utility functions that do not call React hooks should not be named like hooks.
- Shared async helpers should use verb phrases such as `fetchTaskRuns` or `getPlatformSettings`.

---

## Common Mistakes

- Do not move server-only fetching into client hooks without a user-interaction reason.
- Do not duplicate polling or route proxy logic in multiple client components.
- Do not hide request failures behind empty arrays; return or render explicit error state where users need to know the backend failed.

---

## Examples

- Client transition state: `apps/web/components/task-run-actions.tsx`
- Loading/message state: `apps/web/components/generate-daily-report-button.tsx`
- Shared polling helper: `apps/web/lib/task-run-poll.ts`
- Server Actions: `apps/web/app/[locale]/actions.ts`
