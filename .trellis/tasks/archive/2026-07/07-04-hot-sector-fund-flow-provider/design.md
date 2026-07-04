# Hot Sector Fund Flow Provider Design

## Scope

This task upgrades the existing hot-sector surface from a static degraded fixture into a provider-backed contract that can safely display verified or delayed sector performance and fund-flow data when a provider is available, while continuing to show explicit degraded/mock/unavailable states when it is not.

In scope:

- A backend service boundary for hot-sector payload normalization.
- A minimal provider abstraction with deterministic fallback and test provider paths.
- Sector taxonomy metadata for the current MVP sector universe.
- Fund-flow metric definitions, units, source metadata, as-of metadata, and availability metadata.
- Backward-compatible payload fields for the current dashboard UI.
- Frontend support for live, delayed, demo, mock, and unavailable states.
- Focused backend/API/frontend tests and documentation updates.

Out of scope:

- Real-time low-latency terminal-grade sector scanning.
- Trading execution or recommendations based on sector flow.
- Full multi-provider reconciliation.
- Backtesting sector flow signals.

## Current State

`GET /sectors/hot` currently lives in `apps/api/routers/sectors.py` and returns hard-coded static sector fixtures labelled as:

- `status: "degraded"`
- `data_mode: "mock"`
- `source: "static_sector_fixture"`

This is safe because it does not pretend to be live market data, but it lacks provider metadata, as-of timestamps, flow definitions, top constituents, and availability metadata.

The frontend dashboard already renders `HotSectors`, but its data model is fixture-oriented and assumes:

- `data_mode` is one of `live`, `demo`, `mock`, or `none`.
- `fund_flow` uses the Chinese values `流入` / `流出`.
- `fund_flow_amount` is shown as `亿`.
- numeric fields are non-null.

## Sector Taxonomy

The MVP taxonomy is explicit and versioned in the backend service. It covers the current static sector universe used by the dashboard:

- EV & New Energy (`ev_new_energy`)
- Artificial Intelligence (`artificial_intelligence`)
- Semiconductor (`semiconductor`)
- Biotech & Pharma (`biotech_pharma`)
- Consumer Electronics (`consumer_electronics`)

Each sector has:

- `sector_id`
- Chinese and English names
- `market`: `mixed_global` for the current fixture universe
- `taxonomy_version`
- top constituent symbol mapping

The current mapping is not an authoritative exchange taxonomy. It is an MVP product taxonomy used to keep the UI stable until a provider-native taxonomy is integrated.

## Provider Selection

The MVP should introduce a service/provider boundary without marking unverified external data as live by default.

Provider modes:

1. `static_fixture` fallback
   - Always available.
   - Returns mock/degraded payload.
   - Never marked as verified or live.

2. Test/provider-backed path
   - Used by focused tests to prove normalized provider data can be returned as `ok/live` or `ok/delayed`.
   - Keeps the production default safe while establishing the contract for real AkShare/Tushare/Eastmoney style providers.

Future real providers must document:

- Market coverage.
- Permission or token requirements.
- Rate limits.
- Delay/freshness semantics.
- Raw provider field names and definitions.
- Unit and currency.

## Fund-flow Definitions

The normalized payload distinguishes legacy display fields from normalized financial fields.

Legacy compatibility fields retained for the current UI:

- `fund_flow`: localized display direction, currently `流入`, `流出`, `持平`, or `未知`.
- `fund_flow_amount`: display amount in hundred-million currency units for compatibility.

Normalized fields:

- `flow_direction`: `inflow`, `outflow`, `flat`, or `unknown`.
- `net_flow_amount`: signed numeric amount in base currency units.
- `net_flow_currency`: e.g. `CNY`, `USD`, or `N/A`.
- `net_flow_unit`: e.g. `yuan`, `hundred_million`, or `unknown`.
- `flow_window`: e.g. `intraday`, `1d`, or `unknown`.
- `flow_metric`: e.g. `provider_reported_net_inflow` or `static_fixture_demo_value`.
- `flow_definition`: human-readable definition of what the metric means.

Static fixture values must use an explicit mock definition and must not be described as real provider fund flow.

## Normalized Payload Contract

The backend response remains backward-compatible and extends the existing envelope:

```json
{
  "status": "ok | degraded | unavailable",
  "data_mode": "live | delayed | demo | mock | none",
  "source": "provider | static_sector_fixture | backend_proxy",
  "provider": "provider name or null",
  "requested_provider": "requested name or default",
  "effective_provider": "selected provider name",
  "as_of": "ISO timestamp or null",
  "generated_at": "ISO timestamp",
  "is_realtime": false,
  "is_delayed": true,
  "delay_minutes": 15,
  "market": "mixed_global | CN | HK | US",
  "taxonomy_version": "sector-taxonomy-v1",
  "flow_definition": {
    "metric": "provider_reported_net_inflow",
    "window": "intraday",
    "currency": "CNY",
    "unit": "yuan",
    "methodology": "Provider reported net inflow for the sector."
  },
  "availability": {
    "status": "available | delayed | mock | unsupported | unavailable | no_data",
    "reason": "human-readable reason",
    "performance": "available | mock | no_data | unavailable",
    "fund_flow": "available | mock | no_data | unavailable",
    "constituents": "available | mock | no_data | unavailable"
  },
  "message": "human-readable summary",
  "count": 0,
  "items": []
}
```

Each item keeps legacy fields and adds normalized fields:

- `sector_id`
- `name`
- `name_en`
- `market`
- `rank`
- `change_percent`
- `change_window`
- `fund_flow`
- `fund_flow_amount`
- `flow_direction`
- `net_flow_amount`
- `net_flow_currency`
- `net_flow_unit`
- `flow_window`
- `flow_metric`
- `flow_definition`
- `leader_symbol`
- `leader_name`
- `leader_change_percent`
- `leader`
- `symbols_count`
- `top_constituents`
- `as_of`
- `provider`
- `is_verified`
- `availability`

## Data Flow

Backend:

1. `apps/api/routers/sectors.py` validates `limit` and delegates to a service.
2. `packages/services/hot_sectors.py` selects a provider/fallback and normalizes payloads.
3. Provider success returns `ok/live` or `ok/delayed` depending on provider metadata.
4. Provider empty/error/unsupported returns typed degraded/unavailable payloads rather than raising 500.

Frontend:

1. Dashboard server page fetches `/sectors/hot` and passes the typed payload to `HotSectors`.
2. Next API proxy `/api/hot-sectors` preserves the backend payload and normalizes backend/proxy failure into unavailable payloads.
3. `HotSectors` renders state badges, as-of/provider metadata, flow definitions, and sector rows without crashing on partial/null fields.

## Degraded-safe Behavior

- Static fixtures stay `degraded + mock`.
- Unsupported providers return `degraded` or `unavailable` with `data_mode: "none"` and explicit reasons.
- Empty provider results return no fabricated sectors.
- Delayed data is labelled `delayed` and includes `as_of` / `delay_minutes`.
- Mock/demo/stale rankings must never be labelled as verified live fund-flow data.

## UI Behavior

The UI must distinguish:

- Live/verified data.
- Delayed provider data.
- Demo data.
- Mock fixture data.
- Unavailable/no-data state.

The UI should show:

- Provider/source.
- As-of timestamp or unavailable marker.
- Flow definition when present.
- Top constituents when present.
- Strong warning text for mock/demo/degraded data.

## Testing Strategy

Backend/API tests:

- Static fixture fallback remains degraded/mock.
- Provider-backed fake data returns ok/live or ok/delayed with metadata.
- Empty provider response returns no-data/degraded without fabricated rows.
- Unsupported provider returns typed degraded/unavailable payload.
- `limit` validation remains intact.

Frontend tests:

- Next API proxy preserves provider metadata and delayed mode.
- `HotSectors` renders live, delayed, mock, and unavailable states.
- Component does not crash on null/partial numeric fields.
- Dashboard integration still renders hot sectors alongside the rest of the dashboard.

## Rollout and Rollback

Default behavior remains static degraded/mock unless a verified provider path is explicitly selected or injected. If provider integration fails, the service returns typed unavailable/degraded payloads and the UI remains stable.
