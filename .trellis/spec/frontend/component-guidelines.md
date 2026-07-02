# Component Guidelines

> How components are built in this project.

---

## Overview

The frontend uses server-rendered pages for data-heavy screens and small client components for browser interactions. Shared UI primitives live under `apps/web/components/ui`, while domain interaction components live directly under `apps/web/components`.

---

## Component Structure

- Server pages fetch data before rendering, as in `apps/web/app/[locale]/task-runs/page.tsx` and `apps/web/app/[locale]/reports/page.tsx`.
- Client components start with `"use client"`, keep local pending/message state, and call route proxies or Server Actions. Examples: `apps/web/components/task-run-actions.tsx` and `apps/web/components/generate-daily-report-button.tsx`.
- Prefer composition with existing UI primitives such as `Card`, `Table`, `Badge`, and `Button`.
- Use `EmptyState` and `ErrorState` for empty and failed-load branches instead of ad-hoc text blocks.

---

## Props Conventions

- Define a `Props` type near the component.
- Use descriptive prop names such as `taskRunId`, `symbol`, `start`, and `end`.
- Keep component props serializable when the component is used from a server page.
- Use union types for variants when following existing UI primitives, as in `GenerateDailyReportButton`.

---

## Styling Patterns

- Styling is Tailwind class based.
- Prefer existing UI primitives before creating new markup.
- Use layout utility classes directly in page/component JSX, following existing pages.
- Keep class names readable and avoid extracting one-off class constants unless they are reused.

---

## Accessibility

- Use real buttons for actions and links for navigation.
- Keep visible button text translated and assertable in tests, for example the retry button in `task-run-actions.tsx`.
- Table empty/error rows should set `colSpan` to cover all visible columns.

---

## Common Mistakes

- Do not silently render an empty state when the backend request failed; use `ErrorState`.
- Do not add user-visible hardcoded strings outside `apps/web/messages/*.json`.
- Do not duplicate interaction logic when an existing component already covers the flow.
