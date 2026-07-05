# Hot Sector Production Breadth and Rotation History - Design

## Scope

Upgrade the existing hot-sector MVP into a safer professional-sector workflow without pretending that fixture or unavailable provider data is production market signal. The work spans provider verification, backend normalization, optional historical snapshots, frontend rendering, tests, and documentation.

## Current Entry Points

- Backend service: `packages/services/hot_sectors.py`
- Backend API router: `apps/api/routers/sectors.py`
- Frontend proxy: `apps/web/app/api/hot-sectors/route.ts`
- Frontend component: `apps/web/components/hot-sectors.tsx`
- Existing status semantics: `ok`, `degraded`, `unavailable`
- Existing data modes: `live`, `delayed`, `demo`, `mock`, `none`

## Provider Capability Matrix

Provider-specific behavior must be explicit and documented. The implementation should treat provider support as section-level capability rather than assuming a provider can supply every sector metric.

| Capability | Required Semantics | Example Provider State |
|---|---|---|
| Sector ranking | Ranked sectors with change, leader, timestamp, source, and verification flag | Verified / candidate / unavailable |
| Sector fund flow | Net flow amount, unit, direction, flow definition, provider timestamp | Verified / delayed / degraded |
| Constituents | Top constituents with symbol, name, change percent, contribution fields when available | Verified / partial / unavailable |
| Breadth | Advancers, decliners, unchanged, total constituents, breadth ratio | Verified / derived-from-constituents / unavailable |
| Rotation history | Dated snapshots of sector rank, change, flow, and breadth | Stored snapshot / computed current-only / unavailable |
| Taxonomy | Stable sector id, provider taxonomy version, normalized display names | Versioned / provider-specific / unsupported |

Provider failures must produce typed diagnostics and never leak tokens, URLs containing secrets, raw stack traces, or provider-specific private request payloads.

## Payload Design

Extend existing payloads additively so current clients remain compatible.

### Sector Item Additions

- `breadth`: optional object with `advancers`, `decliners`, `unchanged`, `total`, and `advance_decline_ratio`.
- `constituent_contribution`: optional object with top positive and top negative contributors when provider data supports contribution calculations.
- `taxonomy`: optional object with `provider_taxonomy`, `taxonomy_version`, and `normalized_sector_id`.
- `history`: optional compact rotation summary, or a reference to the historical endpoint if separate storage is introduced.

### Rotation Snapshot Shape

Historical storage, if implemented in this task, should preserve enough metadata to prevent stale or mixed-provider interpretation:

- `snapshot_date`
- `captured_at`
- `provider`
- `market`
- `sector_id`
- `rank`
- `change_percent`
- `net_flow_amount`
- `flow_direction`
- `breadth`
- `taxonomy_version`
- `data_mode`
- `verification_status`

If a persistent model or migration is too large for this task, create an explicit follow-up rather than storing opaque JSON in an unrelated table.

## Backend Normalization

The service layer should normalize provider-specific records into a stable public contract. Provider adapters should not leak raw provider field names into UI code.

Rules:

- Keep static fixtures marked as `degraded + mock`.
- Keep unavailable provider paths as `unavailable` with safe diagnostics.
- Allow partial sections: for example, rankings may be available while breadth or rotation history is unavailable.
- Do not infer professional fund-flow fields from daily bars, price-only data, or mock fixtures.
- Keep existing top-constituent rendering backward-compatible.

## Frontend Rendering

`HotSectors` should render new fields progressively:

- Show breadth when present, with concise labels for advancers, decliners, unchanged, and ratio.
- Show contribution leaders/laggards when present.
- Show rotation/history summary only when backed by real snapshot metadata.
- Continue showing clear degraded/unavailable/mock notices when provider support is absent.
- Avoid making unavailable sections look like zero values.

## Documentation Requirements

Update user-facing and developer-facing documentation whenever endpoint fields or provider capability meanings change:

- User docs should explain flow definitions, verification status, delayed/mock/degraded meanings, and why unavailable data is safer than fabricated data.
- Developer docs should explain provider capability states, payload shape, tests, and how to run provider readiness checks.

## Compatibility

- Existing consumers of `/sectors/hot` must continue to work without requiring the new optional fields.
- New fields should be additive and nullable/optional.
- Existing tests for MVP hot sectors must remain valid unless they asserted intentionally incomplete behavior.

## Risks

- Provider schemas may change frequently; tests should cover safe degradation.
- Live provider checks may be flaky; deterministic fixture tests should remain separate from optional live smoke checks.
- Rotation storage can expand the task significantly; do not add persistence without an explicit migration and tests.
