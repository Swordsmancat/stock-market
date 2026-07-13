# Bug Analysis: AkShare zero-row CNINFO request becomes `KeyError`

## 1. Root Cause Category

- **Category**: E - Implicit Assumption, with a D - Test Coverage Gap.
- **Specific cause**: the adapter assumed AkShare would return an empty DataFrame for a valid zero-announcement response. AkShare instead builds an empty frame and selects required columns, which raises `KeyError`. Existing tests covered returned empty frames and arbitrary provider failures, but not this SDK-specific zero-row exception shape.

## 2. Why The Initial Behavior Was Insufficient

1. Catching all `KeyError` as `CNINFO_REQUEST_REJECTED` was fail-safe for schema changes but misclassified a normal empty publication window and caused unnecessary retry backoff.
2. Treating every `KeyError` as empty would fix the symptom but hide real schema regressions when CNINFO still reports announcements.
3. The accepted fix discriminates the two cases with a separate official HTTPS query: only an exact zero count and null/empty announcement list becomes `no_data`.

## 3. Prevention Mechanisms

| Priority | Mechanism | Specific action | Status |
|---|---|---|---|
| P0 | Test coverage | Reproduce an AkShare-style `KeyError` and require independently confirmed empty recovery. | Done |
| P0 | Runtime guard | Fail closed for categories, nonzero counts, malformed payloads, unknown org IDs, and probe errors. | Done |
| P1 | Contract | Document the SDK empty-frame behavior and error matrix in the official disclosure metadata contract. | Done |
| P1 | Live acceptance | Re-run the one-day empty window through Worker/TaskRun and verify zero diagnostics and no duplicate rows/documents. | Done |

## 4. Systematic Expansion

- **Similar issues**: provider wrappers that convert JSON to DataFrames may throw during column selection before returning an expected empty frame.
- **Design improvement**: classify provider exceptions as empty only with independent authoritative evidence; do not infer emptiness from exception class or message alone.
- **Process improvement**: live acceptance should include a known-data window and a known-empty window for every scheduled provider adapter.

## 5. Knowledge Capture

- [x] Updated `.trellis/spec/backend/official-disclosure-metadata-contract.md`.
- [x] Added deterministic provider probe tests.
- [x] Recorded live TaskRun and idempotency evidence.
- [x] Kept the correction within the existing provider boundary; no new cross-layer abstraction was needed.
