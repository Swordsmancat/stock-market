# Implementation plan

1. Add service normalization, catalog projection, exact selection, coherent
   cohort logic, period slicing, serialization, and unit tests.
2. Add the read-only API router, register it, and cover validation/delegation.
3. Add frontend types/helpers and the unified K-line page with URL-owned
   search, asset type, selection, and period controls.
4. Reuse the existing candlestick chart and add localized identity,
   provenance, empty/no-data/error states, and exact detail links.
5. Update Instruments with a compact K-line action and remove provider-capable
   latest fan-out from ordinary list loads through the stored catalog path.
6. Add page/list regressions proving GET-only behavior and no provider or
   mutation requests.
7. Run focused tests, full backend/frontend suites, Ruff, TypeScript, locale
   JSON, Trellis validation, scoped diff checks, and desktop/mobile browser QA.
8. Update the cross-layer code-spec, isolate shared-file hunks, commit, archive,
   and record the session without including parallel dirty tasks.
