# Task-run feedback from user actions - Design

## Summary

This child task connects user-triggered ingestion, analysis, and report generation actions to the existing task-run and report detail destinations. The goal is immediate follow-up visibility: after clicking an action, users should see where to inspect the created background task or generated report.

## Current state

Relevant files:

- `apps/web/app/[locale]/actions.ts`
- `apps/web/app/[locale]/page.tsx`
- `apps/web/app/[locale]/instruments/[symbol]/page.tsx`
- `apps/web/components/generate-daily-report-button.tsx`
- `apps/web/components/ingestion-trigger-form.tsx`
- `apps/web/components/analysis-trigger-form.tsx`
- `apps/web/components/instrument-analysis-forms.tsx`
- `apps/web/components/flash-banner.tsx`
- `apps/web/messages/en.json`
- `apps/web/messages/zh.json`

Current behavior:

- Ingestion and analysis Server Actions redirect with success/error flags but drop available task-run ids.
- Daily report Server Action redirects with success/error flags but drops generated report ids.
- `GenerateDailyReportButton` shows a text message after proxy success but does not link to a generated report or task run.
- Existing task-run and report detail pages already support deep links.

## Target behavior

- Ingestion success redirects include `task_run_id` when the backend response includes one.
- Analysis success redirects include `task_run_id` when the backend response includes one.
- Daily report generation success redirects include `report_id` and `task_run_id` when available.
- Dashboard and instrument detail flash banners render localized links to task-run/report detail pages.
- Client-side report generation shows localized links to the generated report and task run when the proxy response includes ids.
- Failure feedback preserves actionable backend details without dumping raw JSON objects.

## Out of scope

- Redesigning task-run pages.
- Blocking the UI until long-running background work finishes.
- Introducing broad polling outside existing dedicated client components.
- Backend schema changes.
