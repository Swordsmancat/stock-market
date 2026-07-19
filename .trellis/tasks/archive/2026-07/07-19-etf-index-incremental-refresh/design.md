# ETF and Index Incremental Refresh Design

## Boundaries

The change stays inside `packages/services/cn_fund_index_pipeline.py` plus the existing daily-bar coordinator factory in `packages/services/ingestion.py`. Worker, API, schedule, database schema, and read pages keep their signatures.

## Refresh State Projection

After catalog reconciliation, the pipeline loads the bounded active instruments for each asset type. One grouped latest-date subquery joins the latest `DailyBar` row for each selected instrument and projects:

- symbol;
- latest stored trade date;
- latest source;
- latest adjustment.

No new table or migration is needed.

## Window Policy

`CN_FUND_INDEX_INCREMENTAL_OVERLAP_DAYS = 7` is an internal invariant, not another personal setting.

- no latest bar: `symbol_start = global_start`, mode `full_seed`;
- latest bar before end: `symbol_start = max(global_start, latest_date - 7 days)`, mode `incremental`;
- latest bar on/after end: no fetch, mode `current`.

The global `lookback_days` remains authoritative for new instruments and bounds every overlap window.

The worker maps the existing trigger without adding API inputs:

- `trigger="scheduled"` -> incremental window policy;
- `trigger="manual"` -> full requested window for every instrument.

Manual full-window refresh still locks each existing instrument to its stored source/adjustment. Its window mode is `full_refresh`; instruments with no bars remain `full_seed`.

## Source Lock

`build_daily_bar_fetch_coordinator()` accepts an optional exact source for ETF/index ingestion. When supplied, it returns only that source and rejects unknown sources. The pipeline uses the latest stored source for existing instruments:

- `akshare.fund_etf_hist_em` -> `qfq` only;
- `akshare.fund_etf_hist_sina` -> `raw` only;
- `akshare.stock_zh_index_daily` -> `raw` only.

Missing instruments omit the exact source and keep the resilient seed chain. A per-symbol coordinator avoids a permanent circuit-open state suppressing unrelated symbols.

## Results and Failure Semantics

Each asset result adds:

```json
{
  "overlap_days": 7,
  "window_counts": {
    "full_seed": 0,
    "full_refresh": 0,
    "incremental": 1549,
    "current": 0
  }
}
```

The top-level result includes `refresh_mode=incremental|full`. `counts` retains `ingested`, `no_data`, and `failed`, and adds `current`. Provider-wide failure is evaluated against attempted symbols only. An asset with every symbol current is successful with zero bars written.

## Rollback

Reverting the service changes restores full-window requests. Stored bars require no rollback because the implementation only changes request selection and continues using existing upsert/provenance rules.
