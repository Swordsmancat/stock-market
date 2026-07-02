# Task-run feedback from user actions

## Goal

When users trigger ingestion, analysis, or report generation, immediately show where to follow the resulting asynchronous work and what artifact was produced.

The current UI has task-run pages and report/task-run lineage links, but action components do not consistently surface the created task-run or report link at the point of user interaction.

## Requirements

- Action result feedback:
  - Ingestion and analysis triggers should show the created task-run id/link when the backend returns one.
  - Report generation should show a report link and/or task-run link depending on the backend result.
  - Failure messages should preserve actionable backend error detail without exposing sensitive data.
- Frontend interaction model:
  - Keep asynchronous polling optional and scoped to client components if introduced.
  - Avoid blocking the user until long-running tasks finish.
  - Provide clear labels such as "View task run" or "View generated report" in both locales.
- Consistency:
  - Reuse existing route proxies and task-run detail/report detail routes.
  - Keep existing task-run list/detail pages compatible.

## Acceptance Criteria

- [ ] Ingestion trigger success state links to the created task run when available.
- [ ] Analysis trigger success state links to the created task run when available.
- [ ] Report generation success state links to the generated report and/or task run when available.
- [ ] Failed action states display localized, actionable messages.
- [ ] User-visible strings are localized in English and Chinese.
- [ ] Frontend tests cover success links and failure states for affected action components.

## Suggested Validation

```powershell
npm run test:web -- "apps/web/app/[locale]/actions.test.ts" "apps/web/components/generate-daily-report-button.test.tsx"
npm run test:web -- "apps/web/app/[locale]/task-runs/page.test.tsx" "apps/web/app/[locale]/task-runs/[taskRunId]/page.test.tsx"
```

## Notes

- This task should not redesign task-run pages; it should connect user actions to existing destinations.
- If backend action responses lack task-run ids, document the minimal backend response change required.
