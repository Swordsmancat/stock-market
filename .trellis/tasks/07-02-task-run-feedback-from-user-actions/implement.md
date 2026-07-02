# Task-run feedback from user actions - Implementation Plan

## Scope

Improve action feedback links for ingestion, analysis, and daily report generation. Keep the implementation frontend-focused and reuse existing backend/proxy responses.

## Steps

1. Start the Trellis child task.
2. Update `apps/web/app/[locale]/actions.ts`.
   - Extract task-run ids from dispatched responses.
   - Extract generated report ids from daily report responses.
   - Include ids in redirect query params.
   - Convert backend error detail into concise string messages.
3. Update flash rendering.
   - Allow `FlashBanner` messages to contain links.
   - Add dashboard links for ingestion/analysis task runs.
   - Add instrument-detail links for analysis task runs and generated reports.
4. Update `GenerateDailyReportButton`.
   - Parse proxy success payload.
   - Display generated report/task-run links when ids are present.
   - Display actionable failure detail.
5. Update English and Chinese messages together.
6. Update focused tests.
7. Run suggested validation, commit, push, archive, and push archive commit.

## Validation

```powershell
npm run test:web -- "apps/web/app/[locale]/actions.test.ts" "apps/web/components/generate-daily-report-button.test.tsx"
npm run test:web -- "apps/web/app/[locale]/task-runs/page.test.tsx" "apps/web/app/[locale]/task-runs/[taskRunId]/page.test.tsx"
python ./.trellis/scripts/task.py validate .trellis/tasks/07-02-task-run-feedback-from-user-actions
```
