# Implementation

1. Add focused service regressions for partial, complete, tie, failure, and
   zero-write behavior; observe the partial-snapshot failure first.
2. Add a small whole-payload completeness selector in the fundamentals service
   and route eligible partial database reads through it.
3. Update the Eastmoney public fundamentals contract to document whole-snapshot
   selection and its validation matrix.
4. Run focused tests, Ruff, full Python/Web suites, TypeScript, task validation,
   and sanitized live API/browser acceptance for `000001`.
5. Commit only task-owned files, archive, record the journal, and push.
