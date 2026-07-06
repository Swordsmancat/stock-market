# Implementation Plan

## Current Phase

Execution in progress. User approved the reviewed artifacts; implementation is additive and evidence-focused.

## Pre-Development

- [x] Confirm user direction: personal information aggregation, macro/valuation evidence, hard-to-find source collection, and AI summaries over professional trading-terminal competition.
- [x] Create Trellis task.
- [x] Inspect existing macro indicator, source readiness, FRED adapter, dashboard brief, homepage, manual, and runbook contracts.
- [x] Write PRD/design/implementation plan.

## Step 1: Evidence Center Route and Navigation

- [x] Add an evidence route, preferably `apps/web/app/[locale]/evidence/page.tsx`.
- [x] Fetch `GET /dashboard/market-overview` through `backendFetch` using the selected provider.
- [x] Add a localized navigation item in the existing navigation system.
- [x] Add route/page tests for loaded and failed states.

## Step 2: Evidence Summary

- [x] Render `dashboard_brief.narrative.answer_markdown` or deterministic fallback text.
- [x] Show model provider/name, `used_llm`, fallback reason, source-mix counts, and safety flags.
- [x] Show citations and diagnostics while preserving unknown optional fields.
- [x] Test LLM/fallback/source-mix rendering using mocked payloads.

## Step 3: Macro and Valuation Indicator Table

- [x] Render all `macro_indicators.items` or `valuation_indicators.items`.
- [x] Show value/as-of/source when available.
- [x] Show no-data reason when absent.
- [x] Derive and display AI-citable vs not-citable state.
- [x] Show whether source/method metadata is present in `components`.
- [x] Test no-data rows do not render as zero.

## Step 4: Source Readiness and Collection Workflow

- [x] Render grouped `information_sources.groups`.
- [x] Show source status, authority, coverage, freshness policy, AI usage, next action, collection note, citation policy, evidence count, and latest as-of.
- [x] Render collection links with safe external link attributes.
- [x] Render seed-template details: target codes, required fields, JSON preview, CSV preview, checklist, warnings, import command, and citation boundary.
- [x] Test FRED, Buffett Indicator, source status fallback, and generic seed-file examples with a focused route fixture.

## Step 5: Documentation

- [x] Update `docs/manual/user-guide.md` with the Evidence Center workflow.
- [x] Update `docs/runbooks/developer-maintenance.md` with focused validation commands.
- [x] Mention that source links/templates are collection guidance, not citations.

## Validation Commands

Focused checks:

```powershell
npx vitest run "apps/web/app/[locale]/evidence/page.test.tsx" "apps/web/components/navigation-items.test.ts" --reporter=dot
npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0
```

Backend compatibility checks if service contracts are touched:

```powershell
python -m pytest tests/services/test_market_dashboard_service.py tests/services/test_information_sources_service.py tests/api/test_dashboard_api.py -q
```

Full frontend check:

```powershell
npm run test:web -- --reporter=dot
git diff --check
```

## Review Gate

- [x] User reviews PRD/design/implement plan.
- [x] If approved, run `python ./.trellis/scripts/task.py start .trellis/tasks/07-06-macro-valuation-evidence-center`.

## Risk Points

- Keep the first slice additive and evidence-focused.
- Do not create automatic scraping or scheduling.
- Do not cite source-readiness links or seed templates as evidence.
- Do not make no-data values appear as zeros.
- Do not broaden into professional trading-terminal parity.
