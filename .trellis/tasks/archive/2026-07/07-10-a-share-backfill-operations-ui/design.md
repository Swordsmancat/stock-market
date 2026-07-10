# A-share Backfill Operations UI Design

## Data Flow

```text
AI Research server page -> initial no-store coverage
client operations panel -> Next.js proxy -> FastAPI backfill endpoints
mutation success -> coverage refresh/poll -> TaskRun link
```

## Components

- Add `AshareEvidenceCoveragePanel` as a separate client component composed above stock discovery.
- Keep backend payload types in the component and a small shared route helper only where proxy behavior repeats.
- Reuse `FinancialTerminalCard`, `FinancialTerminalSurface`, `Badge`, `Button`, `Table`, `EmptyState`, and `ErrorState` patterns.
- Use local pending/message state and `fetch`; do not add a global state library.

## Routes

- `GET /api/stock-selection/evidence-coverage`.
- `POST /api/ingestion/a-share-evidence-backfills`.
- `GET /api/ingestion/a-share-evidence-backfills/[runId]`.
- `POST` action routes for `resume`, `retry-failed`, and `cancel`.

## Safety

- Mutations use fixed payloads: canary 50/batch 25 or baseline/batch 25.
- UI never accepts raw symbol lists or provider changes.
- Retry previews remain bounded by the backend.
- Baseline/cancel require confirmation; failures remain visible without converting to empty states.
