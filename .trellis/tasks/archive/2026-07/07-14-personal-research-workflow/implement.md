# Personal research workflow implementation plan

## 1. Baseline and regression boundary

- Record current route screenshots/DOM summaries for desktop and mobile,
  especially the protected homepage.
- Run focused existing navigation, homepage, AI Research, Instruments,
  Instrument Detail, Watchlist, Evidence, and Settings tests before edits.
- Confirm `apps/web/app/[locale]/page.tsx` has no task diff throughout work.

## 2. Personal navigation shell

- Reduce the shared navigation source to Home, AI Research, Instruments,
  Watchlist, and Settings in the confirmed order.
- Keep desktop active-state behavior; make mobile five fixed/equal destinations
  without horizontal scrolling or hidden labels.
- Remove the fake account/profile/logout menu while preserving search,
  notifications, language, and theme.
- Add Settings maintenance links for Evidence and Task Runs; preserve contextual
  report, alert, and task links.
- Update shared navigation/top-bar tests and both locale catalogs where needed.

Rollback point: shell changes can be reverted without touching page/API data.

## 3. Bounded instrument discovery

- Add optional `limit`/`offset` to the instrument service/router with additive
  pagination metadata and SQL-side filtering/counting.
- Forward pagination through the existing Next route.
- Add `page` URL state and bounded previous/next navigation to Instruments;
  limit latest-bar and comparison fan-out to the current page.
- Change Global Search to bounded query-on-input instead of full-universe load.
- Add service, API, proxy, page, and client-search regressions for first/middle/
  last pages, filtering, empty results, invalid bounds, and legacy omission.

Rollback point: callers that omit pagination retain the old complete item list.

## 4. Retained personal workflows

- Reorder AI Research so shortlist/discovery/cited analysis precede operational
  coverage and backfill controls; put operations in accessible advanced UI.
- Reorder Instrument Detail so assistant and stored research evidence precede
  unsupported depth/trade/fund-flow panels; group the latter as advanced.
- Simplify Watchlist around saved symbols/open/remove and useful empty recovery;
  keep manual entry and alert editing secondary.
- Reuse existing actions and payloads rather than adding duplicate state or
  watchlist endpoints.
- Update colocated page/component tests and English/Chinese messages together.

Rollback point: composition changes do not alter underlying service contracts.

## 5. Evidence resilience and maintenance hierarchy

- Replace the market-overview early-return coupling with independent fetch
  results so loaded notes/briefs/evidence/disclosures remain visible.
- Render personal notes/briefs before advanced source/ingestion operations.
- Preserve every mutation route, citation boundary, and TaskRun link.
- Add mixed success/failure page tests, not only all-success fixtures.

## 6. Focused Settings and manual LLM test

- Add a backend service and `POST /settings/llm/test` router using the existing
  provider once with a minimal fixed prompt and sanitized stable outcomes.
- Add a same-origin Next POST proxy and focused proxy tests.
- Build a small client Settings control for preset-dependent custom fields and
  one-click test pending/success/error states; keep server-rendered page/form.
- Keep built-in URL/model automatic, expose custom fields only for custom, and
  move provider/news/home-preference internals into advanced sections.
- Assert save never triggers the test, failure never writes settings, blank key
  preservation remains intact, and no public payload contains the key.

Rollback point: remove the isolated test route/control; settings save remains
compatible and deterministic fallback remains available.

## 7. Authorized one-time local cleanup

- Snapshot active watchlist rows and counts.
- Soft-remove exact `TEST:US` and `CN_SHANGHAI_COMPOSITE:CN` rows through the
  existing service/API after rollout; do not create generic cleanup code.
- Verify both rows are inactive, other tables/rows are unchanged, and the new
  empty Watchlist state is usable.
- Record sanitized before/after evidence without connection strings or secrets.

## 8. Verification and rollout

- Run focused backend tests for instruments/settings and focused web tests for
  every changed page/component/proxy/action.
- Run Ruff/mypy on touched Python, TypeScript, full backend and full web suites,
  locale JSON parsing, Trellis validation, and `git diff --check`.
- Browser-verify 1440x1000, 390x844, and 375px widths in light/dark modes:
  primary navigation, deep links, core ordering, advanced disclosure, empty/
  degraded states, keyboard labels, no overlap, and no horizontal overflow.
- Compare the protected homepage before/after DOM structure and screenshots;
  any main-content regression fails acceptance.
- Invoke the new manual LLM test once against the configured local DeepSeek
  runtime, record only sanitized model/latency/status evidence, and do not retry.
- Confirm Web 3000, API 8000, Worker, and Beat remain healthy.
