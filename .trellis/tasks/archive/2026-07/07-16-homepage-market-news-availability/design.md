# Homepage market and news availability design

## Boundaries

The fix stays at four existing ownership boundaries. The YFinance and AkShare
adapters own wire-row validity. The market-dashboard service owns the bounded
CN-index source decision. The cache decorator owns whether an aggregate is safe
to reuse. The FastAPI router owns whether synchronous service work occupies the
event loop. The homepage remains a server component consuming the same payloads.

## Data flow

```text
yfinance frame
  -> normalize MultiIndex columns
  -> parse required finite OHLCV
  -> skip invalid rows
  -> ProviderBar list
  -> market overview projection
  -> reject contradictory ok/latest-close-null cache writes
  -> unchanged homepage payload

homepage SSR
  -> news/latest GET --------------------------> sync FastAPI worker -> DB
  -> dashboard/market-overview GET -> sync worker -> DB/provider/cache

yfinance CN-index payload
  -> complete and valid -----------------------> unchanged yfinance item
  -> empty or invalid -> one AkShare Sina call -> complete fallback item
                       -> empty/failure --------> truthful degraded item
```

## Provider contract

`YFinanceProvider.fetch_bars(symbol, "1d", start, end)` reuses the existing
`_decimal_or_none()` finite-number parser already used by minute bars. A row is
emitted only when all five required OHLCV values are present and finite. Zero
volume remains valid. The adapter does not repair or interpolate an invalid row.

AkShare exposes a dedicated Sina index-daily method using
`stock_zh_index_daily`. It applies the exchange prefix from the canonical index
definition, bounds rows to the requested dates, normalizes the standard
date/OHLCV schema, and emits only complete finite rows. This path is separate
from the existing A-share stock downloader and does not change stock fallback.

## Index fallback contract

`_serialize_market_index()` keeps `get_bars_payload(..., provider_name="yfinance")`
as the primary call. Only CN indices requested through yfinance are eligible.
If the complete primary payload has no usable finite rows, the service invokes
the dedicated AkShare Sina index method once and builds one replacement payload
from those rows. Rows from the two sources are never combined.

Fallback success identifies AkShare and `akshare.stock_zh_index_daily` as the
effective provider/source while preserving yfinance as the requested provider.
An empty fallback keeps explicit no-data. A provider/schema failure becomes a
sanitized unavailable diagnostic containing no URL, response body, Cookie, or
credentials. Non-CN indices, followed instruments, and non-yfinance requests
never enter this path.

## Cache contract

`cache_market_overview()` evaluates the result before `redis.set`. For the
`followed.items` and `indices.items` projections, every item with `status="ok"`
must contain a mapping `latest` with a finite numeric `close`. Boolean values do
not count as numeric prices. Explicit `no_data` and `unavailable` items are not
contradictory and may be cached.

The guard is defensive: provider filtering should prevent the current defect,
while the cache rule prevents a future provider or serializer regression from
amplifying one bad response for five minutes.

## Scheduling contract

Change the dashboard route from `async def` to `def`. FastAPI then executes the
synchronous service in its worker threadpool, allowing unrelated async request
dispatch to continue. No new executor, background job, retry, or timeout is
introduced.

## Compatibility and rollout

- No database migration, frontend payload change, or cache-key change.
- No Cookie/login state, database writes, retry loop, or generic crawler.
- Existing contradictory market-overview cache entries are cleared once after
  the fixed API process is loaded.
- Reload only the API process required to activate backend source changes;
  leave PostgreSQL, Redis, workers, Beat, and the web service available.
- Rollback is the scoped work commit. Cache invalidation is safe because the
  payload is read-through and recomputable.

## Docker runtime contract

The default Compose project owns the normal personal-use stack. Its web service
reuses `Dockerfile.web.acceptance`, binds Next.js to `0.0.0.0:3000`, uses
`http://api:8000` for server-side calls, and publishes
`http://127.0.0.1:8000` for browser-side calls. PostgreSQL and Redis health
checks gate API startup; API health gates worker, Beat, and web startup.
`restart: unless-stopped` preserves Docker Desktop restart behavior. The
separate `stock-acceptance` Compose project and its 13000/18000 ports remain
unchanged.
