# Implementation Plan

## Current Phase

Planning. Do not start implementation until the user approves these artifacts.

## Pre-Development

- [x] Confirm user direction: personal information aggregation, macro/valuation evidence, hard-to-find source collection, and AI summaries over professional trading-terminal competition.
- [x] Create Trellis task.
- [x] Inspect existing macro indicator, source readiness, FRED adapter, dashboard brief, homepage, manual, and runbook contracts.
- [x] Write PRD/design/implementation plan.

## Step 1: Evidence Center Route and Navigation

- [ ] Add an evidence route, preferably `apps/web/app/[locale]/evidence/page.tsx`.
- [ ] Fetch `GET /dashboard/market-overview` through `backendFetch` using the selected provider.
- [ ] Add a localized navigation item in the existing navigation system.
- [ ] Add route/page tests for loaded and failed states.

## Step 2: Evidence Summary

- [ ] Render `dashboard_brief.narrative.answer_markdown` or deterministic fallback text.
- [ ] Show model provider/name, `used_llm`, fallback reason, source-mix counts, and safety flags.
- [ ] Show citations and diagnostics while preserving unknown optional fields.
- [ ] Test LLM/fallback/source-mix rendering using mocked payloads.

## Step 3: Macro and Valuation Indicator Table

- [ ] Render all `macro_indicators.items` or `valuation_indicators.items`.
- [ ] Show value/as-of/source when available.
- [ ] Show no-data reason when absent.
- [ ] Derive and display AI-citable vs not-citable state.
- [ ] Show whether source/method metadata is present in `components`.
- [ ] Test no-data rows do not render as zero.

## Step 4: Source Readiness and Collection Workflow

- [ ] Render grouped `information_sources.groups`.
- [ ] Show source status, authority, coverage, freshness policy, AI usage, next action, collection note, citation policy, evidence count, and latest as-of.
- [ ] Render collection links with safe external link attributes.
- [ ] Render seed-template details: target codes, required fields, JSON preview, CSV preview, checklist, warnings, import command, and citation boundary.
- [ ] Test FRED, Buffett Indicator, PBOC/manual, future documents, and generic seed-file examples.

## Step 5: Documentation

- [ ] Update `docs/manual/user-guide.md` with the Evidence Center workflow.
- [ ] Update `docs/runbooks/developer-maintenance.md` with focused validation commands.
- [ ] Mention that source links/templates are collection guidance, not citations.

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

- [ ] User reviews PRD/design/implement plan.
- [ ] If approved, run `python ./.trellis/scripts/task.py start .trellis/tasks/07-06-macro-valuation-evidence-center`.

## Risk Points

- Keep the first slice additive and evidence-focused.
- Do not create automatic scraping or scheduling.
- Do not cite source-readiness links or seed templates as evidence.
- Do not make no-data values appear as zeros.
- Do not broaden into professional trading-terminal parity.
