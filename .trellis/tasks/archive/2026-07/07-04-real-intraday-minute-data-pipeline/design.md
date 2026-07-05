# Real Intraday Minute Data Pipeline Design

## Scope

Upgrade the existing intraday chart contract from a degraded-only endpoint into a provider-backed minute-bar pipeline for one verified provider path, while preserving explicit degraded or no-data behavior for providers that cannot provide verified minute bars.

This task covers:

- Backend provider contract additions for intraday minute bars.
- A yfinance MVP implementation for `1m` minute bars.
- Service-layer normalization for `/market-data/{symbol}/intraday`.
- Frontend type and rendering compatibility for real minute-bar payloads.
- Focused backend/frontend tests and documentation updates.

This task does not cover:

- Level-2 order book or tick-by-tick trade data.
- Persisting minute bars to the database.
- Production SLA, entitlement, or real-time streaming semantics.
- AkShare/Tushare minute-bar integration beyond explicitly keeping them unsupported until verified.

## Current State

`GET /market-data/{symbol}/intraday?date=YYYY-MM-DD&timeframe=1m` exists, but `packages.services.market_data.get_intraday_bars_payload` currently returns a degraded payload for every provider. The current degraded contract is valuable and must stay intact for unsupported provider paths.

Current provider risks:

- `mock` accepts `timeframe="1m"` but returns one row per day, so it must not be treated as real minute data.
- `akshare` and `tushare` currently use daily APIs and do not have verified minute-bar support in this backend.
- `yfinance` currently only supports `fetch_bars(..., timeframe="1d")`, but yfinance itself can fetch `interval="1m"` data. It is the best MVP candidate because the repository already has a yfinance provider boundary and normalization tests.

## Provider Contract

Add an explicit intraday provider boundary instead of reusing daily `fetch_bars("1m")`.

Recommended backend model:

```python
@dataclass(frozen=True)
class ProviderIntradayBar:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    amount: Decimal | None = None
    average_price: Decimal | None = None

class IntradayProviderAdapter(Protocol):
    provider_name: str

    def fetch_intraday_bars(
        self,
        symbol: str,
        trade_date: date,
        timeframe: str,
    ) -> list[ProviderIntradayBar]:
        ...
```

Only providers with verified minute-bar support should implement this method. Service code should check capability via `hasattr(provider, "fetch_intraday_bars")` or a narrow protocol helper; it must not call daily `fetch_bars("1m")` for providers that have not implemented explicit intraday support.

## MVP Provider: yfinance

yfinance MVP behavior:

- Support only `timeframe="1m"`.
- Download with `interval="1m"`, `start=trade_date`, `end=trade_date + 1 day`.
- Normalize yfinance `DatetimeIndex` rows into `ProviderIntradayBar` items.
- Preserve minute timestamps as ISO-serializable datetimes.
- Return an empty list for empty provider responses, weekends, holidays, historical dates outside yfinance's minute-data retention window, and malformed rows that cannot be normalized.
- Set `average_price=None` and `amount=None` unless a verified provider field exists.
- Keep previous-close calculation separate from minute data. Daily data can be used for previous-close reference only; it must not fabricate minute bars.

## Service Payload Contract

Keep the public endpoint and query parameters unchanged:

```text
GET /market-data/{symbol}/intraday?date=YYYY-MM-DD&timeframe=1m&provider=yfinance
```

Successful provider payload:

```json
{
  "symbol": "AAPL",
  "timeframe": "1m",
  "date": "2026-07-03",
  "source": "provider",
  "provider": "yfinance",
  "requested_provider": "yfinance",
  "effective_provider": "yfinance",
  "status": "ok",
  "previous_close": 213.55,
  "items": [
    {
      "timestamp": "2026-07-03T13:30:00+00:00",
      "open": 214.1,
      "high": 214.3,
      "low": 213.9,
      "close": 214.2,
      "price": 214.2,
      "average_price": null,
      "volume": 12000,
      "amount": null
    }
  ],
  "availability": {
    "status": "ok",
    "reason": null,
    "is_realtime": false,
    "is_delayed": true,
    "delay_minutes": null
  }
}
```

Empty verified provider response:

- `status="no_data"`
- `source="provider"`
- `items=[]`
- `availability.status="no_data"`
- reason explains that no verified minute bars were returned for that trade date.

Unsupported provider response:

- Keep `status="degraded"`.
- Keep `source="none"`.
- Keep `items=[]`.
- Keep the explicit unsupported reason.

Unsupported timeframe:

- Continue raising `ValueError`, which the FastAPI router maps to HTTP 400.

## Previous Close

`previous_close` is a reference line, not minute-bar data. It can be sourced from daily bars by looking back several calendar days before `trade_date` and taking the most recent verified daily close.

Rules:

- Do not fail the whole intraday payload if previous close is unavailable.
- Return `previous_close=null` when no prior daily close is available.
- Do not use daily bars to create intraday item rows.

## Frontend Behavior

The existing frontend already supports `status="ok"` minute points in `IntradayPriceChart` by normalizing `timestamp`, `price`/`close`, `average_price`, and `volume`.

Expected changes:

- Ensure `InstrumentIntradayPayload` can carry the real provider payload without local shape loss.
- Keep backend proxy fallback behavior for failed intraday requests.
- Add tests proving an `ok` intraday payload is passed through and rendered.
- If the backend introduces a new `unavailable` status later, update frontend union types and empty-state copy in the same change. This MVP should prefer existing `degraded` for unsupported providers to reduce cross-layer churn.

## Data Flow

```text
Browser / detail page
  -> Next route proxy / instrument detail fetcher
  -> FastAPI GET /market-data/{symbol}/intraday
  -> packages.services.market_data.get_intraday_bars_payload
  -> yfinance provider explicit fetch_intraday_bars
  -> normalized minute payload
  -> IntradayPriceChart
```

## Testing Strategy

Backend:

- Provider tests for yfinance minute DataFrame normalization, interval forwarding, empty response, and malformed/missing column behavior.
- Service tests for yfinance `ok`, `no_data`, unsupported provider degraded, unsupported timeframe, and previous-close lookup.
- API tests for real minute payload and unsupported provider degraded response.

Frontend:

- Proxy test for preserving real intraday `ok` payload.
- Page/detail test proving real intraday data reaches `IntradayPriceChart`.
- Component test already covers `status="ok"`; add only focused coverage if a new status or field behavior is introduced.

Documentation:

- Update user manual and developer runbook with yfinance minute-data support, limitations, and fallback behavior.

## Rollout and Rollback

Rollout is safe because unsupported providers remain degraded and the existing endpoint shape is preserved.

Rollback path:

- Disable the yfinance intraday branch in the service capability check.
- Keep provider method code unused until fixed.
- Frontend continues to display degraded states with no page-level failure.
