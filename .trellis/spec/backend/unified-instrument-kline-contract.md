# Unified Stored Instrument K-Line Contract

## Scenario: Read-Only Stock ETF And Index Daily K-Lines

### 1. Scope / Trigger

- Trigger: a personal user searches stored stocks, ETFs, or indexes and opens
  one exact daily K-line series.
- Scope: `packages/services/instrument_kline.py`,
  `packages/services/stored_daily_bars.py`, `GET /instrument-kline`, the
  Instruments list, Global Search, and `/[locale]/instruments/kline`.
- Non-goals: provider refresh, ingestion, backfill, intraday data, futures,
  AI conclusions, portfolio mutation, recommendations, or trading.

### 2. Signatures

- Service:
  `get_instrument_kline_payload(*, session, query=None, asset_type=None, symbol=None, market=None, period="3m", limit=20, offset=0) -> dict[str, object]`.
- API:
  `GET /instrument-kline?q=<text>&asset_type=stock|etf|index&symbol=<exact>&market=<exact>&period=1m|3m|6m|1y&limit=1..50&offset>=0`.
- Page: `GET /[locale]/instruments/kline` with search, type, exact identity,
  and period stored in the URL.

### 3. Contracts

- Read active `Instrument`, `Market`, `Exchange`, and `DailyBar` rows directly
  from the injected session. Never call a provider, crawler, ingestion,
  backfill, fixture, seed, AI, portfolio, order, or trading path.
- The catalog includes only `stock`, `etf`, and `index`, uses stable
  market/type/symbol ordering, bounded pagination, and latest stored-bar
  metadata. Instruments and Global Search consume this same projection.
- Exact selection requires both normalized symbol and market. A missing exact
  identity is `not_found`; never substitute another market or search match.
- Choose one coherent `provider + adjustment` cohort by largest row count,
  then lexical provider and adjustment tie-break. Anchor the requested period
  to that cohort's latest stored date and never splice price bases.
- Exclude non-finite, non-positive, inverted OHLC, or negative-volume rows.
  Return bounded diagnostics; never fabricate prices or volume.
- Expose distinct `empty`, `not_found`, `no_data`, and `ready` states plus
  database source, provenance, coverage, pagination, and research/no-trading
  safety metadata.
- The Instruments page performs one catalog read, not per-row latest-provider
  requests. Workspace navigation is GET-only and preserves the five-item
  mobile navigation.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Unknown type/period, overlong query, invalid limit/offset | HTTP 422; no database projection work |
| Only symbol or only market supplied | HTTP 422; exact identity remains mandatory |
| No selection | `empty`; bounded catalog remains available |
| Exact identity missing or inactive | `not_found`; never substitute |
| Identity exists without a valid coherent cohort | `no_data`; preserve identity and diagnostics |
| Multiple cohorts exist | Select one deterministic coherent cohort |
| Invalid stored OHLCV row | Drop it and report bounded diagnostics |
| Database/API failure | Render localized failure, not an empty result or provider fallback |

### 5. Good / Base / Bad Cases

- Good: the user filters ETFs, selects `CN/510300`, and receives one stored
  `akshare/qfq` series anchored to its latest date with exact provenance.
- Base: an index exists with no stored bars; catalog and identity remain
  visible while the workspace shows `no_data`.
- Bad: page load calls yfinance, combines raw and adjusted rows, guesses a
  market from a duplicate symbol, or silently replaces an API failure with
  seed data.

### 6. Tests Required

- Service tests cover normalization, supported types, stable pagination,
  exact identity, cohort selection, period anchoring, numeric safety, and all
  explicit states.
- API tests cover validation and injected-session delegation.
- Decoder/proxy tests reject non-database payloads and preserve GET query
  identity without caching.
- Workspace tests cover URL-owned search/type/selection/period state,
  provenance, chart data, exact detail links, and distinct failure states.
- Instruments and Global Search tests prove the shared catalog contract and
  absence of `/market-data/*/latest` fan-out.
- Browser acceptance covers desktop and `390x844`, nonblank stored charts,
  and no page-level horizontal overflow.

### 7. Wrong vs Correct

#### Wrong

```python
bars = provider.fetch_daily_bars(symbol)
series = sorted(raw_rows + qfq_rows, key=lambda row: row.trade_date)
```

This makes browsing network-dependent and combines incompatible price bases.

#### Correct

```python
catalog = query_supported_stored_instruments(session, query, asset_type)
cohort = choose_daily_bar_cohort_key(stored_cohort_counts)
series = query_exact_cohort(session, instrument.id, cohort, period_window)
```

The catalog, identity, price basis, and observation window stay deterministic.
