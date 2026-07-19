# CN ETF and Index Ingestion Contract

## 1. Scope / Trigger

- Trigger: populate the database-only CN ETF and index K-line workspaces from public AkShare sources.
- Scope: provider normalization, asset-isolated universe persistence, sequential daily-bar ingestion, TaskRun observability, API dispatch, and Beat scheduling.
- Non-goals: page-load provider calls, logged-in sessions, cookies, trading, intraday data, or combining bars with incompatible adjustments.

## 2. Signatures

- Provider: `AkShareProvider.fetch_instrument_universe(market, asset_type="stock") -> ProviderInstrumentUniverseSnapshot`.
- Daily bars: `AkShareProvider.fetch_etf_bars(...)`, `fetch_sina_etf_bars(...)`, and `fetch_index_bars(...)`.
- Service: `sync_cn_fund_index_data(session, start, end, max_symbols_per_type, request_delay_seconds, incremental=True, ...) -> dict[str, object]`.
- Worker: `ingestion.sync_cn_fund_index_data`.
- API: `POST /ingestion/cn-fund-index-pipeline?lookback_days=120&max_symbols_per_type=5000`.
- DB identity: `instruments(market_id, symbol, asset_type)` is unique; `instrument_universe_syncs.asset_type` identifies catalog history.

## 3. Contracts

- Catalog order is ETF then index. Daily bars use the same order and one symbol request at a time.
- ETF catalog source is `akshare.fund_etf_spot_em`.
- Index catalog primary is `akshare.stock_zh_index_spot_em`; an exception, empty frame, or unusable schema switches the entire snapshot to `akshare.stock_zh_index_spot_sina`.
- A fallback catalog never merges rows with the primary. `snapshot.source` and persisted sync history identify the effective source.
- ETF daily bars try `akshare.fund_etf_hist_em` with `qfq`, then `akshare.fund_etf_hist_sina` with `raw` under `cn_resilient` policy.
- Index daily bars use `akshare.stock_zh_index_daily` with `raw`.
- Daily-bar fallback selects one coherent source for the requested range. It never stitches `qfq` and `raw` rows.
- Scheduled worker delivery (`trigger=scheduled`) uses a seven-calendar-day overlap from each instrument's latest stored bar. Missing instruments still use the complete configured lookback; instruments already current through `end` make no provider request.
- Manual worker/API delivery (`trigger=manual`) preserves the complete requested lookback window.
- Existing ETF refreshes are locked to their latest stored source and adjustment. Only an ETF with no bars may use the Eastmoney-to-Sina cross-adjustment seed fallback.
- Refresh state is loaded through one bounded latest-row projection, not one database query per symbol.
- Task results identify `refresh_mode` and per-asset `window_counts` for `full_seed`, `full_refresh`, `incremental`, and `current`.
- Provider diagnostics store stable codes, bounded counts, source names, and exception types only. Raw responses and exception messages are forbidden.
- Environment keys are `CN_FUND_INDEX_PIPELINE_ENABLED`, `CN_FUND_INDEX_PIPELINE_CRON_HOUR`, `CN_FUND_INDEX_PIPELINE_CRON_MINUTE`, `CN_FUND_INDEX_PIPELINE_LOOKBACK_DAYS`, `CN_FUND_INDEX_PIPELINE_MAX_SYMBOLS_PER_TYPE`, and `CN_FUND_INDEX_PIPELINE_REQUEST_DELAY_MS`.
- Reads remain database-only through `/instrument-kline`; read pages never enqueue refresh work.

## 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Unsupported market or asset type | Reject with `ValueError`; make no provider request for unsupported markets |
| Primary index catalog succeeds with usable rows | Persist only the primary source |
| Primary index catalog fails or is unusable; Sina succeeds | Persist only Sina rows and `INSTRUMENT_UNIVERSE_FALLBACK_USED` |
| Both index catalogs fail or are unusable | Persist unavailable sync history, preserve last good catalog, and stop with `CN_INDEX_CATALOG_UNAVAILABLE` |
| Eastmoney ETF bars fail; Sina succeeds | Store Sina bars with `source_priority=1`, `adjustment=raw`, and fallback metadata |
| Scheduled existing ETF has Sina/raw bars | Refresh the seven-day overlap from Sina only; do not call Eastmoney |
| Scheduled existing ETF has Eastmoney/qfq bars | Refresh from Eastmoney only; do not fall back across adjustment cohorts |
| Scheduled instrument is already current through `end` | Count `current`, make no provider call, and keep the run successful |
| Manual API dispatch | Refresh the complete requested lookback while retaining the stored source lock |
| Existing source/adjustment is unsupported | Fail that symbol with a stable diagnostic; do not expose or silently replace provenance |
| Every sampled bar request for one asset fails or returns no data | Stop with `CN_<ASSET>_DAILY_BARS_PROVIDER_WIDE_FAILURE`; retain earlier catalog and bar commits |
| Fresh pipeline TaskRun already exists | Suppress the overlapping run using the existing fresh-run guard |

## 5. Good / Base / Bad Cases

- Good: a scheduled run refreshes existing Sina/raw ETFs directly over a seven-day overlap, skips already-current instruments, and full-seeds only newly listed ETFs.
- Base: primary sources succeed; fallback downloaders are not called.
- Bad: retry Eastmoney for every known Sina ETF, treat a manual 730-day request as incremental, label Sina rows as Eastmoney, stitch raw and qfq bars, persist provider response bodies, or trigger provider calls from K-line reads.

## 6. Tests Required

- Provider tests assert normalization, deterministic dedupe, prefixed Sina symbols, source selection, fallback diagnostics, and secret-safe failures.
- Universe service tests assert `(market, symbol, asset_type)` coexistence, asset-isolated deactivation, last-good preservation, and effective fallback source persistence.
- Ingestion tests assert ETF/index source routing, resilient ETF fallback, source attempts, adjustment, and source priority.
- Pipeline/worker/API/schedule tests assert sequential order, bounded inputs, overlap suppression, TaskRun progress, dispatch, and Beat registration.
- Incremental tests assert seven-day overlap, exact-source locks, current skips, new-instrument seeding, scheduled/manual trigger mapping, and attempted-only provider-wide failure.
- Migration tests assert legacy rows become `stock` and asset-aware uniqueness is applied.
- Live acceptance requires non-zero ETF/index catalogs and at least one stored recent series for each type, followed by database-only K-line API/page reads.

## 7. Wrong vs Correct

### Wrong

```python
# Loses provenance and may combine incompatible rows.
bars = eastmoney_qfq_bars + sina_raw_bars
source = "akshare.fund_etf_hist_em"
```

### Correct

```python
DailyBarSource(source="akshare.fund_etf_hist_em", adjustment="qfq", priority=0)
DailyBarSource(source="akshare.fund_etf_hist_sina", adjustment="raw", priority=1)
# The coordinator validates and selects one source for the whole request.
```

For an existing instrument, correct incremental construction narrows that list to its stored cohort:

```python
build_daily_bar_fetch_coordinator(
    "akshare",
    "etf",
    exact_source=latest_bar.source,
)
```
