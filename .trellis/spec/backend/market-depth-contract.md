# Market Depth Contract

## Scenario: Explicit Provider-Backed Market Depth

### 1. Scope / Trigger

- Trigger: `GET /market-data/{symbol}/depth` now has an explicit provider boundary for order book, recent trades, large orders, and fund-flow sections.
- Scope: provider models in `packages/providers/base.py`, candidate provider adapters such as `packages/providers/akshare_provider.py`, service orchestration in `packages/services/market_data.py`, FastAPI routing in `apps/api/routers/market_data.py`, readiness diagnostics in `scripts/provider_readiness.py`, and frontend consumers under `apps/web`.
- Non-goals: low-latency streaming, paid entitlement management, persistent tick storage, order execution, and fabricating Level-2 from daily or minute bars.

### 2. Signatures

- API: `GET /market-data/{symbol}/depth?depth_levels=<positive-int>&large_order_threshold_amount=<positive-decimal>&provider=<provider>`
- Service: `get_market_depth_payload(symbol, provider_name=None, depth_levels=5, large_order_threshold_amount=None) -> dict[str, object]`
- Provider method: `fetch_market_depth(symbol: str, depth_levels: int) -> ProviderMarketDepthSnapshot`
- Provider models: `ProviderOrderBookLevel`, `ProviderRecentTrade`, `ProviderFundFlow`, `ProviderMarketDepthSnapshot`
- Readiness smoke: `python scripts/provider_readiness.py --provider <provider> --market <market> --symbol <symbol> --check-depth --depth-levels <n> --real-network`

### 3. Contracts

- Only explicit `fetch_market_depth` provider methods may produce real depth rows.
- `fetch_bars`, `fetch_intraday_bars`, static fixtures, mock providers, and estimated volume distributions must never populate order-book, recent-trade, large-order, or fund-flow sections.
- Top-level `status="ok"` means at least one verified section has provider rows or provider fund-flow values.
- Top-level `status="degraded"` means the provider is unsupported, failed, empty, malformed, or every production-sensitive section is unavailable.
- `source="provider"` is allowed only for explicit market-depth snapshots.
- `source="none"` is used for unsupported providers or failed candidate paths.
- Section statuses are independent: `order_book.status="ok"` may coexist with `recent_trades.status="degraded"` and `fund_flow.status="degraded"`.
- Large orders are derived only from verified recent trades and the explicit `large_order_threshold_amount`; if a trade lacks `amount`, compute `price * volume` only when both fields came from the verified provider trade row.
- Candidate providers, including AkShare, stay candidate/degraded until an opt-in live smoke succeeds and the provider capability matrix is updated.

### 4. Validation & Error Matrix

- `depth_levels <= 0` -> FastAPI validation error `422`.
- `large_order_threshold_amount <= 0` -> FastAPI validation error `422`.
- Unknown provider -> router maps service `ValueError` to HTTP `400`.
- Provider without `fetch_market_depth` -> HTTP `200`, top-level `status="degraded"`, all sections empty/degraded, capability metadata false.
- Provider returns empty snapshot -> HTTP `200`, degraded/no-data sections, no fabricated rows.
- Provider exception or schema change -> readiness emits `FAIL` with safe diagnostics such as exception type or raw shape metadata; runtime payload remains degraded and secret-safe.
- Partial provider support -> top-level `ok` only when at least one section is verified; unavailable sections remain degraded with reasons.
- Live smoke failure -> do not promote provider capability; preserve fixture-tested candidate wording in docs.

### 5. Good/Base/Bad Cases

- Good: a verified provider snapshot returns bid/ask levels, recent trades, and fund-flow values; service serializes section payloads, derives large orders from recent trades, and frontend renders real rows.
- Base: AkShare parser tests can normalize injected order-book shaped payloads, but live smoke fails with `ConnectionError`; docs and capability matrix call it a candidate path, not production Level-2.
- Bad: unsupported `yfinance` or `mock` provider falls back to daily bars or minute bars to create fake bids, asks, trades, or fund-flow values.
- Bad: large-order rows are derived from daily volume or estimated turnover instead of verified recent trades.

### 6. Tests Required

- Provider tests assert candidate adapters parse injected depth payloads and return degraded snapshots for empty, unavailable, or malformed inputs.
- Service tests assert explicit provider snapshots serialize all sections, partial sections remain degraded, large-order thresholds are honored, and unsupported providers do not call daily or intraday methods.
- API tests assert request validation, unknown-provider errors, provider metadata, and section-level payload shapes.
- Readiness script tests assert `--check-depth` is opt-in, non-writing, and reports unsupported/live-failure diagnostics without tracebacks or secrets.
- Frontend route/component/page tests assert Next proxies preserve payloads and `MarketDepthCard` renders real rows and degraded sections distinctly.
- Full project checks should include focused backend tests, focused frontend depth tests, `python -m pytest -q`, `npm run test:web`, and `git diff --check`.

### 7. Wrong vs Correct

#### Wrong

```python
# Do not infer market depth from daily bars.
bars = provider.fetch_bars(symbol, "1d", start, end)
return {
    "status": "ok",
    "order_book": {"bids": [{"price": bars[-1].close, "volume": bars[-1].volume}]},
}
```

#### Correct

```python
fetch_market_depth = getattr(provider, "fetch_market_depth", None)
if not callable(fetch_market_depth):
    return build_degraded_market_depth_payload(...)

snapshot = fetch_market_depth(symbol, depth_levels)
return serialize_market_depth_snapshot(
    snapshot,
    large_order_threshold_amount=threshold_amount,
)
```
