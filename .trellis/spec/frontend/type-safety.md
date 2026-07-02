# Type Safety

> Type safety patterns in this project.

---

## Overview

The frontend uses TypeScript with local payload types close to pages and components. Runtime validation is currently light; most code casts backend JSON to local types after calling `response.json()`.

---

## Type Organization

- Define page-specific payload types in the page file, such as `TaskRun` and `TaskRunsPayload` in `apps/web/app/[locale]/task-runs/page.tsx`.
- Define component prop types near the component, such as `TaskRunRetryButtonProps`.
- Keep API route handler parameter types explicit, for example `params: Promise<{ taskRunId: string }>`.
- Use `Record<string, unknown>` for generic JSON objects when practical.

---

## Validation

- The project does not currently use Zod or another runtime validation library.
- When accepting wrapped backend payloads, handle both expected and legacy shapes where existing pages already do this, such as task-run detail payload unwrapping.
- For route proxies, preserve upstream status and content type unless there is a deliberate transformation.

---

## Common Patterns

- Cast `await response.json()` to a local payload type at the API boundary.
- Keep formatting and extraction helpers near the page when they are page-specific.
- Use explicit unions for known statuses when rendering localized labels, while preserving unknown backend status strings.

---

## Known Type Debt

- Some dynamic links use `as any` to satisfy next-intl typed routing with dynamic path strings.
- Some JSON fields still use `any`, for example historical `result_json` handling.
- Future cleanup should add shared route helpers or stronger JSON types rather than spreading more local casts.

---

## Examples

- Local task-run types: `apps/web/app/[locale]/task-runs/page.tsx`
- Wrapped task-run detail payload handling: `apps/web/app/[locale]/task-runs/[taskRunId]/page.tsx`
- API proxy params typing: `apps/web/app/api/task-runs/[taskRunId]/retry/route.ts`
- Route proxy test typing: `apps/web/app/api/task-runs/[taskRunId]/retry/route.test.ts`
