# Bug analysis: empty watchlist resurrected configured placeholders

## 1. Root cause category

- **Category**: D / E - test coverage gap plus implicit assumption.
- **Specific cause**: `_default_watchlist_value()` assumed an empty successful
  database result meant configuration was unavailable. In this domain, empty
  is also an intentional state created by soft removal. Existing tests covered
  bootstrap, non-empty persistence, soft removal, and worker failure
  separately, but not their composition across the service/worker boundary.

## 2. Why earlier behavior survived

There was no failed repair attempt in this session; the first implementation
change addressed the reproduced root cause. The bug survived the earlier
personal-workflow cleanup because that cleanup correctly verified the public
watchlist stayed empty, while the scheduled worker's independent fallback path
was not included in the cleanup regression set.

## 3. Prevention mechanisms

| Priority | Mechanism | Specific action | Status |
| --- | --- | --- | --- |
| P0 | Test coverage | Compose historical inactive rows with the scheduled worker; also cover explicit empty scope with a reused TaskRun | Done |
| P0 | Executable specification | Document successful empty read versus `SQLAlchemyError` fallback and the exact skipped payload | Done |
| P1 | Runtime verification | Queue one zero-provider task through the replacement worker and inspect its terminal TaskRun | Done |
| P2 | Review heuristic | When a persisted collection can be intentionally empty, reject `value or default` unless empty and missing are contractually identical | Captured in the domain spec |

## 4. Systematic expansion

- **Similar issues**: a scoped search found no other collection-to-settings
  fallback matching this pattern. Ordinary provider/name defaults use scalar
  values and do not share the intentional-empty contract.
- **Design improvement**: no new abstraction is justified. Distinguishing
  `None`/exception from an empty collection at the existing worker boundary is
  sufficient and keeps the personal workflow simple.
- **Process improvement**: a one-time cleanup that changes active scope must
  include scheduled consumers of that scope, not only the public read model.

## 5. Knowledge capture

- [x] Added the worker regression test.
- [x] Added the empty persisted watchlist scenario to backend error-handling
      specifications.
- [x] Recorded direct and queued runtime acceptance evidence.
- [x] No template sync was possible or needed because this application
      repository has no `src/templates/markdown/spec/` tree.
- [x] No follow-up architecture ticket is warranted for this bounded fix.
