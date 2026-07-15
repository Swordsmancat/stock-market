# Automatic multi-source data and news fallback design

## Boundary

The feature extends existing provider and persistence boundaries rather than
adding a generic crawler. Exact instrument identity remains `(symbol, market)`.
The browser owns one-shot automatic intent, backend services own source order
and validation, and only persisted news may enter AI citations.

## Data flows

### Daily bars

```text
detail/API request
  -> market-scoped database rows
  -> one coherent database cohort
  -> if the database is coherent: return it
  -> if mixed provenance leaves insufficient coverage:
       requested provider
       -> AkShare Eastmoney daily
       -> AkShare Sina daily
       -> configured Tushare daily
  -> return first complete validated single-source series
  -> otherwise retain the degraded non-empty database cohort
```

`DailyBarFetchCoordinator.fetch` gains an optional required coverage window.
A non-empty source that does not cover that window records
`insufficient_coverage` and the coordinator continues. Existing callers that
omit the option retain current behavior.

The database remains authoritative when it contains one coherent cohort. A
mixed cohort triggers recovery only when the complete stored range is at least
the existing research-readiness size while the newest coherent cohort is not.
No GET path writes canonical bars.

### Intraday minutes

```text
exact symbol + market + date
  -> existing future/weekend/holiday policy
  -> historical closed-session cache
  -> requested provider
  -> AkShare stock_zh_a_hist_min_em
  -> AkShare stock_zh_a_minute
  -> ok | no_data | degraded
```

A small intraday coordinator mirrors daily source-attempt semantics but uses
`ProviderIntradayBar`. It validates exact symbol/date, timestamp ordering,
duplicates, finite OHLCV/amount, OHLC consistency, and non-negative volume.
AkShare naive timestamps are localized to Asia/Shanghai before serialization.

Cache metadata remains provider-specific while `bars_1m` remains the canonical
fact table. Before a successful fallback cache write, stale cache metadata for
other providers with the same symbol/date/timeframe is removed so metadata
cannot claim ownership of rows written by a later source.

### News

```text
GET detail -> stored NewsArticle only

empty detail client -> one POST refresh
  -> stored-news preflight
  -> configured implemented search providers in saved order
  -> AkShare stock news for exact CN symbol
  -> market-aware yfinance news
  -> normalize candidates
  -> reject social/public-opinion persistence
  -> dedupe and persist NewsArticle + SentimentSignal
  -> return sanitized refresh metadata + final stored-news projection
```

The existing aggregate `GET /news/search` behavior remains compatible. The new
refresh service is sequential and stop-on-first-persisted-success. AkShare and
yfinance adapters return normalized `NewsSearchCandidate` values without
writing; persistence remains centralized in
`persist_news_search_candidates`.

`POST /news/{symbol}/refresh?market=<market>` is the public mutation. It never
accepts keys, cookies, arbitrary provider URLs, or raw HTML. A bounded
`GET /news/latest?limit=<n>` returns stored rows across symbols for the
homepage.

## Frontend state

Instrument detail keeps server-rendered stored news in `initialData`. A small
client controller receives serializable labels and:

1. skips when news already exists;
2. records `news-fallback:v1:{market}:{symbol}:{date}` in `sessionStorage`
   before the request;
3. calls one same-origin POST proxy;
4. replaces only `data.news` with the returned stored projection;
5. never automatically retries after any terminal result;
6. allows one explicit retry command.

Visible states are `idle`, `recovering`, `recovered`, `no_data`,
`provider_error`, and `unsupported`. Backend diagnostic codes map to localized
copy. Backend messages are not rendered.

Homepage remains read-only. It uses the global latest stored-news endpoint and
represents `loaded-empty` separately from `failed`.

## Compatibility and trade-offs

- Existing route fields are additive; old clients continue to ignore market,
  provenance, attempts, and refresh metadata.
- Existing news search aggregation and settings stay available. Automatic
  detail refresh uses the dedicated sequential service.
- A complete single-source daily series is preferred over stitching sources.
  This may omit a newest day when every complete provider is behind, but avoids
  mixing price adjustments and preserves auditable evidence.
- Automatic news refresh is limited to one exact detail page and one browser
  attempt per local day. This accepts a small page-load mutation because the
  user explicitly requested automatic recovery, while avoiding homepage-wide
  fan-out.
- Public crawling remains an adapter boundary, not a generic parser. Login
  state and cookies never cross into this service.

## Rollout and rollback

- Keep normal `3000/8000` serving during development and tests.
- Validate in-process services and an isolated Web/API stack before replacing
  normal processes.
- Reload only Web/API after all checks. Leave PostgreSQL, Redis, Worker, Beat,
  queued work, and five-day acceptance evidence untouched.
- Rollback is restarting the prior Web/API revision and disabling the new
  automatic client controller; stored deduplicated news remains valid local
  evidence and does not require deletion.
