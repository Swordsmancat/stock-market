# Frontend Development Guidelines

> Project-specific frontend conventions for the stock analysis platform.

---

## Overview

The frontend is a Next.js App Router application under `apps/web`. It uses server components for data-heavy pages, Server Actions for form mutations, route handlers under `apps/web/app/api/**` as client-facing backend proxies, `next-intl` for English/Chinese localization, shadcn-style UI primitives, and Vitest + Testing Library for page and interaction tests.

These guidelines document the current codebase. They are intentionally descriptive rather than aspirational.

---

## Pre-Development Checklist

- Read the relevant guideline file below before editing frontend code.
- Search for an existing page/component/action/proxy pattern before creating a new one.
- Keep user-visible text in `apps/web/messages/en.json` and `apps/web/messages/zh.json` unless it is raw data from the backend.
- For page changes, update or add the colocated Vitest page test when behavior changes.
- Do not commit or push from implementation subagents.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | App Router, components, lib, i18n, API proxy, and test layout | Filled |
| [Component Guidelines](./component-guidelines.md) | Server/page components, client components, UI composition, empty/error states | Filled |
| [Hook Guidelines](./hook-guidelines.md) | Current minimal custom-hook usage and client-side async patterns | Filled |
| [State Management](./state-management.md) | Server data, URL state, Server Actions, local pending/message state | Filled |
| [Quality Guidelines](./quality-guidelines.md) | Vitest, Testing Library, i18n, route proxy, and interaction testing | Filled |
| [Type Safety](./type-safety.md) | Local payload types, typed-route casts, JSON payload handling, type debt | Filled |

---

## Common Frontend Entry Points

- Dashboard page: `apps/web/app/[locale]/page.tsx`
- Task runs page: `apps/web/app/[locale]/task-runs/page.tsx`
- Task run detail page: `apps/web/app/[locale]/task-runs/[taskRunId]/page.tsx`
- Server Actions: `apps/web/app/[locale]/actions.ts`
- Backend fetch helper: `apps/web/lib/backend-api.ts`
- API proxy example: `apps/web/app/api/task-runs/[taskRunId]/retry/route.ts`
- UI state components: `apps/web/components/empty-state.tsx`, `apps/web/components/error-state.tsx`
- Translation files: `apps/web/messages/en.json`, `apps/web/messages/zh.json`

---

**Language**: These project guidelines are written in English so subagents can consume them consistently.
