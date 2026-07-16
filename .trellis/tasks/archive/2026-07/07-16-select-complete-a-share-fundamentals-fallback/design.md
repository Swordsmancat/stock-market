# Design

## Boundary

The selection stays inside `packages/services/fundamentals.py`. Provider
parsing, API shape, frontend rendering, and persistence schemas do not change.

## Data Flow

1. Read the latest stored snapshot at or before the requested date.
2. Return immediately for non-CN, disabled-gate, or complete stored snapshots.
3. For an eligible partial snapshot, resolve the normalized Eastmoney public
   payload through the existing cache/provider path.
4. Count non-null core metrics in each whole snapshot.
5. Return the public payload only when its score is strictly greater.
6. Otherwise enrich the stored payload through the existing company-only path.

## Coherence And Safety

- Selection is whole-snapshot; fields from different report dates are never
  merged.
- A tie favors stored data to avoid unnecessary provenance changes.
- Public no-data/unavailable payloads cannot replace usable stored evidence.
- The existing public adapter owns URL, timeout, byte/row bounds, redirect,
  proxy, credential, diagnostic, and cache behavior.
- No session write or commit is introduced.

## Rollback

Reverting the service selection helper restores company-only enrichment. No
schema or persisted data migration is involved.
