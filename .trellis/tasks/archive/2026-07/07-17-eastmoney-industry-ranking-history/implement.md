# Implementation plan

1. Add secret-safe Eastmoney proxy/Cookie platform settings and tests.
2. Add the provider adapter with direct-first/proxy-fallback transport,
   response validation, fixtures and sanitised failures.
3. Add the ranking model and migration, then implement transactional refresh,
   deterministic ranking and bounded database-only projection tests.
4. Add sectors API routes and Web proxy/action contracts.
5. Add the localized Evidence Center matrix, controls, empty/error states and
   component/page tests.
6. Validate focused tests, full backend/Web suites, type checking, migration,
   JSON catalogs, secret scans and Trellis Check.
7. Run a real refresh when a working configured access path is present; deploy
   only affected services and verify ports 3000 and 8000.
8. Update the data-source/spec documentation, complete the PRD, commit, push,
   archive the task and record the journal.

## Rollback points

- Settings/provider can land without enabling any automatic request.
- The additive table and DB-only read path are harmless while empty.
- The UI panel can be removed independently without deleting stored history.
