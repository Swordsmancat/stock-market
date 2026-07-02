# Directory Structure

> How frontend code is organized in this project.

---

## Overview

Frontend code lives in `apps/web` and follows Next.js App Router conventions. Locale-aware pages are under `apps/web/app/[locale]`, client-facing route-handler proxies are under `apps/web/app/api`, reusable UI and interaction components are under `apps/web/components`, and shared helpers are under `apps/web/lib`.

---

## Directory Layout

```text
apps/web/
  app/
    [locale]/        localized pages and Server Actions
    api/             route-handler proxies to the FastAPI backend
  components/        shared UI and client interaction components
  lib/               backend fetch, dates, polling, settings helpers
  messages/          next-intl translation catalogs
  src/i18n/          next-intl routing and request configuration
  test/              Vitest setup and framework mocks
```

---

## Module Organization

- Add navigable pages in `apps/web/app/[locale]/<route>/page.tsx`.
- Keep route-specific tests beside pages, for example `apps/web/app/[locale]/task-runs/page.test.tsx`.
- Add client-facing backend proxies under `apps/web/app/api/**/route.ts` when browser code must call the backend through Next.js.
- Add reusable UI and interaction components under `apps/web/components`.
- Add cross-cutting helpers under `apps/web/lib`.
- Add English and Chinese user-facing strings to `apps/web/messages/en.json` and `apps/web/messages/zh.json`.

---

## Naming Conventions

- Route folders use App Router conventions such as `task-runs`, `[taskRunId]`, and `reports/[reportId]`.
- Shared component files use kebab-case, such as `generate-daily-report-button.tsx` and `task-run-actions.tsx`.
- Tests use colocated names such as `page.test.tsx` and `route.test.ts`.
- Keep local payload types near the page or route that consumes them unless multiple files share the same contract.

---

## Examples

- Dashboard server page: `apps/web/app/[locale]/page.tsx`
- Task runs page: `apps/web/app/[locale]/task-runs/page.tsx`
- Task run detail page: `apps/web/app/[locale]/task-runs/[taskRunId]/page.tsx`
- Server Actions: `apps/web/app/[locale]/actions.ts`
- API proxy route: `apps/web/app/api/task-runs/[taskRunId]/retry/route.ts`
- Backend fetch helper: `apps/web/lib/backend-api.ts`
- i18n routing: `apps/web/src/i18n/routing.ts`
- Vitest setup: `apps/web/test/setup.ts`
