# Implement ingestion single fetch

## Goal

Refactor ingestion so a single provider snapshot drives the returned payload, database writes, `bar_count`, and `quality_diagnostics`.

## Requirements

- Use the archived design `.trellis/tasks/archive/2026-07/07-02-design-ingestion-single-fetch/design.md` as the source of truth.
- Keep `get_market_snapshot(...)` public behavior unchanged.
- Remove the session-backed duplicate provider fetch from `ingest_market_snapshot(...)`.
- Write database rows from the same serialized snapshot used for response and diagnostics.
- Preserve the existing processed-bar `bar_count` semantics.
- Preserve current upsert behavior for duplicate instrument/date bars.
- Parse serialized timestamps explicitly and fail clearly on unsupported timestamp values.
- Convert serialized numeric values safely before assigning database numeric columns.
- Do not change provider adapters, API route contracts, or database schema.

## Acceptance Criteria

- [x] Session-backed ingestion calls provider instrument fetch once per ingestion call.
- [x] Session-backed ingestion calls provider bar fetch once per instrument per ingestion call.
- [x] Session-backed and no-session ingestion compute `bar_count` from the serialized snapshot.
- [x] Database writes, returned payload, and `quality_diagnostics` are derived from the same snapshot.
- [x] Empty instrument snapshots still return the existing quality failure payload and zero bars.
- [x] Duplicate bars for the same instrument/date preserve last-write-wins behavior while counting processed bars.
- [x] Focused ingestion/data-quality tests pass.

## Validation

```bash
python -m pytest tests/services/test_ingestion_service.py tests/services/test_data_quality.py -v
```

## Notes

- Expected production file: `packages/services/ingestion.py`.
- Expected test file: `tests/services/test_ingestion_service.py`.
- This child should run before TaskRun diagnostics persistence.
