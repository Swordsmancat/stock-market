# Real Market Depth Provider Pipeline Design

## Scope

Upgrade the market-depth feature from a hard-coded degraded contract into an explicit provider-backed depth pipeline boundary. The design must preserve degraded-safe behavior and support section-level partial availability for order book, recent trades, large orders, and fund-flow data.

This task covers:

- Provider contract models for market-depth snapshots.
- Service-layer orchestration for verified depth providers and unsupported providers.
- Section-level status and capability metadata.
- Large-order filtering from verified recent trades only.
- Frontend rendering of real rows and partial degraded sections.
- Documentation and tests for no-fabrication guarantees.

This task does not cover:

- Low-latency streaming order flow.
- Exchange entitlement management or paid Level-2 feeds.
- Persisting depth/tick data.
- Treating daily bars, intraday bars, static fixtures, or mock volume distributions as real depth data.

## Current State

`GET /market-data/{symbol}/depth?depth_levels=5&large_order_threshold_amount=1000000` currently returns a degraded payload for every configured provider. The route and UI already support a rich shape with `order_book`, `recent_trades`, `large_orders`, `fund_flow`, and capability metadata, but the backend does not call a real provider for those sections.

Current provider state:

- `mock`: not real depth; must remain degraded.
- `yfinance`: has daily bars and yfinance `1m` intraday bars, but no verified order book, tick, or fund-flow path; must remain degraded for depth.
- `akshare`: the most realistic public-data candidate for A-share order book / recent trades / fund-flow, but repository code currently only uses daily bars. It must be integrated through explicit depth methods and fixture-backed parser tests before capability can be enabled.
- `tushare`: possible moneyflow/tick candidate, but permission/token/points requirements are uncertain. Keep unsupported until entitlement and schema are verified.

## Provider Contract

Add explicit market-depth models instead of reusing daily or intraday bars.

Recommended models:

```python
@dataclass(frozen=True)
class ProviderOrderBookLevel:
    price: Decimal
    volume: Decimal
    amount: Decimal | None = None
    order_count: int | None = None

@dataclass(frozen=True)
class ProviderRecentTrade:
    timestamp: datetime
    price: Decimal
    volume: Decimal
    amount: Decimal | None = None
    side: str | None = None

@dataclass(frozen=True)
class ProviderFundFlow:
    currency: str | None
    net_inflow: Decimal | None = None
    main_net_inflow: Decimal | None = None
    retail_net_inflow: Decimal | None = None
    source_definition: str | None = None

@dataclass(frozen=True)
class ProviderMarketDepthSnapshot:
    provider: str
    source: str
    as_of: datetime | None
    is_realtime: bool
    is_delayed: bool
    delay_minutes: int | None
    bids: list[ProviderOrderBookLevel]
    asks: list[ProviderOrderBookLevel]
    recent_trades: list[ProviderRecentTrade]
    fund_flow: ProviderFundFlow | None = None
    availability: dict[str, object] = field(default_factory=dict)

class MarketDepthProviderAdapter(Protocol):
    def fetch_market_depth(
        self,
        symbol: str,
        depth_levels: int,
    ) -> ProviderMarketDepthSnapshot:
        ...
```

Only `fetch_market_depth` may populate real depth rows. Service code must never call `fetch_bars` or `fetch_intraday_bars` to infer order book, recent trades, large orders, or fund-flow.

## Provider Strategy

MVP strategy is staged:

1. **Contract-safe stage**: introduce provider-depth models, service normalization, partial-section payloads, and tests using injected provider fixtures. Keep production provider capabilities degraded unless a provider explicitly returns normalized depth snapshots.
2. **AkShare candidate path**: add an optional AkShare depth method behind explicit downloader injection and parser tests. If the runtime AkShare call fails, returns empty data, or cannot be normalized, the service returns degraded/no-data sections instead of fabricated rows.
3. **Live verification gate**: only documentation and capability matrix should describe AkShare as verified after a real-network smoke check is run manually/opt-in. Default CI tests remain fixture-based and offline.

## Service Payload Contract

Keep the public endpoint unchanged:

```text
GET /market-data/{symbol}/depth?depth_levels=5&large_order_threshold_amount=1000000&provider=akshare
```

Top-level behavior:

- `status="ok"` only when at least one verified section has real rows or verified fund-flow values.
- `status="degraded"` when provider does not support verified depth or every section is unavailable.
- `source="provider"` only for explicit depth provider snapshots.
- `source="none"` for unsupported providers.

Section behavior:

- `order_book.status="ok"` only when bids or asks came from verified provider order-book rows.
- `recent_trades.status="ok"` only when recent trades came from verified provider tick/trade rows.
- `large_orders.status="ok"` only when derived from verified `recent_trades` using the explicit threshold.
- `fund_flow.status="ok"` only when provider returns a documented fund-flow definition and values.
- Unsupported sections remain `degraded` with reason and empty/null values.

## Large Orders

Large orders are derived only from verified recent trades:

- Input: normalized `ProviderRecentTrade` rows.
- Threshold: `large_order_threshold_amount` request value or default `1,000,000`.
- A trade qualifies when `amount >= threshold`; if `amount` is missing, service may compute `price * volume` only if both fields are verified provider fields.
- Never derive large orders from daily volume, minute volume, or mock data.

## Frontend Behavior

`MarketDepthCard` already renders real rows when provided. Expected enhancements:

- Preserve existing degraded UI.
- Render section-level real rows for order book, recent trades, large orders, and fund-flow.
- Make partial support clear: top-level `ok` can coexist with section-level `degraded`, and the UI should show unavailable sections distinctly.
- Keep fallback behavior in `apps/web/lib/instrument-detail.ts` for failed depth requests.

## Data Flow

```text
Instrument detail page
  -> Next route proxy / instrument detail fetcher
  -> FastAPI GET /market-data/{symbol}/depth
  -> packages.services.market_data.get_market_depth_payload
  -> explicit provider fetch_market_depth if supported
  -> normalized section payloads
  -> MarketDepthCard
```

## Testing Strategy

Backend:

- Provider-model serialization tests.
- Service tests for real injected provider snapshots.
- Unsupported provider tests proving daily/intraday/mock data is not used.
- Empty provider response / malformed payload / provider failure tests.
- Large-order threshold tests from verified recent trades.
- API tests for real provider fixture path, partial section support, and existing 422/400 behavior.

Frontend:

- `MarketDepthCard` test for partial sections and section-level degraded reasons.
- Next instrument proxy test preserving real depth payloads.
- Instrument detail page test passing real depth payload to `MarketDepthCard`.

Documentation:

- Update user guide and developer runbook with real-depth limitations, capability matrix, and no-fabrication rules.

## Rollout and Rollback

Rollout is safe if unsupported providers stay degraded and real rows are only produced by explicit depth methods.

Rollback path:

- Disable provider capability routing for depth.
- Leave UI and contract degraded-safe fallback intact.
- Keep provider parser code unused until fixed.
