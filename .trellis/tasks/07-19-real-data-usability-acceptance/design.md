# Real-data usability acceptance design

## Boundary

The running database and existing GET projections are authoritative. The
acceptance first observes API and page behavior without mutation. UI changes
may only improve explanation of an already structured state; they must not
invent a second data model or call a provider.

## State classification

| State | Meaning | Required presentation |
| --- | --- | --- |
| `selection_required` | The workflow needs user input | Explain the required selection; do not call it missing data |
| `catalog_uncollected` | No stored instruments exist for the selected type | Name the missing asset coverage and point to operational data pages |
| `not_found` | Exact stored identity is absent | Preserve the requested identity and explain it was not found |
| `series_unavailable` | Identity exists but no coherent stored series exists | Preserve identity and provenance diagnostics |
| `partial_evidence` | Some topic sections are ready and others empty | Render ready sections and section-specific empty reasons independently |
| `load_failure` | API/database request failed | Use the existing localized error state, never an empty state |

## Data flow

The existing flow remains `PostgreSQL -> service -> FastAPI GET -> Next server
page`. Runtime acceptance uses only GET requests and browser navigation. Any
copy improvement is derived from existing payload status, catalog totals,
selected identity, and section status.

## Compatibility and rollback

No API or database contract change is planned. Localization keys and page
branches are additive. Rollback is limited to reverting the page/message/test
changes; stored data and collection schedules are unaffected.
