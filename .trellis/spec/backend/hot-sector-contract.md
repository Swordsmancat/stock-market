# Hot Sector Contract

> Executable contract for the `/sectors/hot` hot-sector and fund-flow endpoint.

## Scenario: Provider-Backed Hot Sector Metadata

### 1. Scope / Trigger

- Trigger: `/sectors/hot` changed from a simple sector list into a cross-layer provider-backed contract consumed by FastAPI, Next.js route proxies, dashboard pages, and the `HotSectors` component.
- Applies to `packages/services/hot_sectors.py`, `apps/api/routers/sectors.py`, `apps/web/app/api/hot-sectors/route.ts`, and `apps/web/components/hot-sectors.tsx`.
- Static fixtures, demo data, and unavailable providers must remain visibly non-production.
- Additive InStock-inspired daily context parameters (`sector_type`, `window`) are owned by this contract even when the rows are rendered alongside market daily data.

### 2. Signatures

- Backend API: `GET /sectors/hot?limit=<1..10>&provider=<optional-provider>&sector_type=industry|concept&window=today|5d|10d`
- Service entry point: `get_hot_sectors_payload(limit: int = 5, provider_name: str | None = None, provider: HotSectorFundFlowProvider | None = None, sector_type: str | None = None, window: str | None = None) -> dict[str, object]`
- Provider boundary: `HotSectorFundFlowProvider.fetch_hot_sectors(limit: int, sector_type: str = "industry", window: str = "today") -> HotSectorProviderResult`

### 3. Contracts

Top-level response fields:

- `status`: `ok` / `degraded` / `unavailable`
- `data_mode`: `live` / `delayed` / `demo` / `mock` / `none`
- `source`, `provider`, `requested_provider`, `effective_provider`
- `as_of`, `generated_at`, `is_realtime`, `is_delayed`, `delay_minutes`
- `sector_type`: normalized requested sector taxonomy, defaulting to `industry`
- `window`: normalized fund-flow window, defaulting to `today`
- `taxonomy_version`
- `flow_definition`: `{ metric, window, currency, unit, methodology }`
- `availability`: section-level availability, including `performance`, `fund_flow`, `constituents`, `breadth`, `constituent_contribution`, `rotation_history`, and `taxonomy`
- `provider_capabilities`: section-level capability statuses for ranking, fund flow, constituents, breadth, contribution, rotation history, and taxonomy
- `items`: sector rows

Sector item additive fields:

- `breadth`: advancers, decliners, unchanged, total, A/D ratio, status, source or reason
- `constituent_contribution`: top positive and top negative contributors, status, metric or reason
- `taxonomy`: provider taxonomy, normalized sector id, taxonomy version
- `history`: rotation-history summary; unavailable unless real snapshots or provider history exists

### 4. Validation & Error Matrix

- Unknown provider -> HTTP 200 payload with `status="unavailable"`, `data_mode="none"`, empty `items`, and unavailable provider capabilities.
- Unsupported `sector_type` -> HTTP 200 payload with `status="unavailable"`, empty `items`, and a sanitized message naming `industry` / `concept` as supported values.
- Unsupported `window` -> HTTP 200 payload with `status="unavailable"`, empty `items`, and a sanitized message naming `today`, `5d`, and `10d` as supported values.
- Provider exception -> HTTP 200 payload with `source="provider_error"` and sanitized message containing exception type but no token, key, raw URL secret, or stack trace.
- Static fixture -> `status="degraded"`, `data_mode="mock"`, `source="static_sector_fixture"`, `is_verified=false`.
- Provider returns no rows -> `status="degraded"`, `data_mode="none"`, empty `items`, section-level unavailable capability metadata.
- Missing breadth/contribution/history inputs -> unavailable section payloads, never zero-filled values.

### 5. Good / Base / Bad Cases

- Good: verified provider rows include sector ranking, fund-flow metadata, constituents, derived breadth, contribution leaders, taxonomy, and explicit unavailable rotation history when snapshots do not exist.
- Good: omitting `sector_type` and `window` preserves the previous default industry/today hot-sector behavior.
- Good: `sector_type=concept&window=5d` requests provider-backed concept flow without introducing a second sector-ranking route.
- Base: static fixture renders dashboard shape while every production-sensitive field remains `mock` or `degraded`.
- Bad: using daily bars, mock rows, or missing provider fields to fabricate live fund flow, Level-2, breadth, contribution, or rotation history.

### 6. Tests Required

- Service tests assert static fixture is degraded mock, unknown provider is unavailable, unsupported `sector_type` / `window` return unavailable payloads, provider failure is sanitized, live provider rows normalize breadth/contribution/taxonomy, and empty providers do not fabricate rows.
- API tests assert `/sectors/hot` preserves top-level status, provider capability metadata, additive item fields, and `sector_type` / `window` query propagation.
- Frontend proxy tests assert upstream query/status/payload propagation, including optional `sector_type` and `window`.
- Component/page tests assert visible live/delayed/mock/unavailable states and that missing numeric fields do not crash rendering.

### 7. Wrong vs Correct

#### Wrong

```python
return {
    "status": "ok",
    "data_mode": "live",
    "breadth": {"advancers": 0, "decliners": 0},
    "items": static_fixture_rows,
}
```

#### Correct

```python
return {
    "status": "degraded",
    "data_mode": "mock",
    "source": "static_sector_fixture",
    "availability": {"breadth": "mock", "rotation_history": "unavailable"},
    "provider_capabilities": {
        "breadth": {"status": "mock"},
        "rotation_history": {"status": "unavailable"},
    },
    "items": static_fixture_rows,
}
```
