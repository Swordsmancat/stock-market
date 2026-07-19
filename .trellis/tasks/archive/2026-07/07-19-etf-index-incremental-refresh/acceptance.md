# ETF and Index Incremental Refresh Acceptance

> Accepted: 2026-07-19

## Baseline

- Complete baseline TaskRun: `66f2a5f8-5e8e-453a-8a15-5f3aa7030c0e`.
- ETF catalog coverage: 1,549 / 1,549 with 117,727 stored daily bars.
- Index catalog coverage: 550 / 550 with 43,992 stored daily bars.

## Bounded Scheduled-Mode Run

- TaskRun: `ddd1fbf8-d277-43ec-b3bd-9978fd230f77`.
- Inputs: 120-day global lookback, maximum three symbols per asset type, `trigger=scheduled`.
- Result: `succeeded`, pipeline `status=ok`, `refresh_mode=incremental`.
- ETF: three incremental windows, three ingested, 18 bars, zero no-data/failed/current; all used `akshare.fund_etf_hist_sina`.
- Index: three incremental windows, three ingested, 18 bars, zero no-data/failed/current; all used `akshare.stock_zh_index_daily`.
- ETF catalog remained 1,549 active instruments. Index catalog used its documented Sina snapshot fallback and remained 550 active instruments.

## Provenance Verification

Direct read-only PostgreSQL checks covered the three bounded symbols for each asset type:

- ETFs `159001`, `159003`, and `159005` each have exactly one stored source and one adjustment: `akshare.fund_etf_hist_sina/raw`.
- Indexes `000001`, `000002`, and `000003` each have exactly one stored source and one adjustment: `akshare.stock_zh_index_daily/raw`.
- Every sampled series remained current through the latest trading date, 2026-07-17.

## Runtime Health

- Worker and Beat restarted successfully and registered `ingestion.sync_cn_fund_index_data`.
- API `http://127.0.0.1:8000/health` returned HTTP 200 after the run.
- Web `http://127.0.0.1:3000/zh` returned HTTP 200 after the run.
- PostgreSQL and Redis remained healthy; the normal 3000/8000 stack was not replaced or stopped.

## Conclusion

The scheduled path now refreshes bounded per-instrument overlap windows, preserves existing source/adjustment cohorts, seeds only new instruments with the resilient fallback chain, and keeps manual dispatch compatible with full-window refreshes.
