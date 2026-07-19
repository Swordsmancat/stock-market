# CN ETF and Index Ingestion Runbook

## Purpose

The `ingestion.sync_cn_fund_index_data` pipeline maintains stored CN ETF and index catalogs plus recent daily bars. The storage and K-line pages read only PostgreSQL.

## Data Sources

| Dataset | Priority | AkShare function | Stored source | Adjustment |
| --- | ---: | --- | --- | --- |
| ETF catalog | 0 | `fund_etf_spot_em` | `akshare.fund_etf_spot_em` | n/a |
| Index catalog | 0 | `stock_zh_index_spot_em` | `akshare.stock_zh_index_spot_em` | n/a |
| Index catalog fallback | 1 | `stock_zh_index_spot_sina` | `akshare.stock_zh_index_spot_sina` | n/a |
| ETF daily bars | 0 | `fund_etf_hist_em` | `akshare.fund_etf_hist_em` | `qfq` |
| ETF daily-bar fallback | 1 | `fund_etf_hist_sina` | `akshare.fund_etf_hist_sina` | `raw` |
| Index daily bars | 0 | `stock_zh_index_daily` | `akshare.stock_zh_index_daily` | `raw` |

Catalog and bar fallbacks replace the failed source for that request. Rows from different catalog sources or adjustments are never merged.

## Automatic Schedule

The default Beat schedule runs on CN weekdays at 19:15 Shanghai time. Configure it with the `CN_FUND_INDEX_PIPELINE_*` keys documented in `.env.example`. Only one fresh run may execute at a time.

Scheduled runs are incremental after the first baseline:

- instruments without bars receive the complete configured lookback;
- existing instruments refresh a seven-calendar-day overlap from their latest stored date;
- instruments already current through the target date make no provider request;
- existing ETFs stay locked to their stored source and adjustment, so `qfq` and `raw` are not mixed.

Manual API runs remain full-window operations. Use them when intentionally extending or rebuilding the configured historical range.

## Manual Bounded Run

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/ingestion/cn-fund-index-pipeline?lookback_days=120&max_symbols_per_type=3"
```

Use a small symbol limit for provider acceptance. The production default can cover the stored active catalog sequentially and respects `CN_FUND_INDEX_PIPELINE_REQUEST_DELAY_MS`.

## Verification

Check the Crawler Monitor for the `fund_index_cn` pipeline. A successful result reports catalog sources, per-asset counts, bar counts, source distributions, and bounded diagnostics.

`refresh_mode` is `incremental` for Beat and `full` for manual dispatch. `window_counts` separates `full_seed`, `full_refresh`, `incremental`, and `current` instruments.

Database checks should confirm:

- active `etf` and `index` instruments are non-zero;
- `instrument_universe_syncs.source` matches the effective catalog source;
- `bars_1d.source`, `adjustment`, and `source_priority` match the selected bar source;
- `/instrument-kline?asset_type=etf...` and `asset_type=index...` return `source=database` and `status=ready` for stored samples.

## Failure Handling

- `CN_ETF_CATALOG_UNAVAILABLE` or `CN_INDEX_CATALOG_UNAVAILABLE`: both usable catalog paths were unavailable; last good active rows remain intact.
- `CN_ETF_DAILY_BARS_PROVIDER_WIDE_FAILURE` or `CN_INDEX_DAILY_BARS_PROVIDER_WIDE_FAILURE`: no sampled symbol produced bars; earlier catalog and symbol commits remain intact.
- Provider errors must be represented by stable codes and exception types. Do not copy raw response bodies, request URLs with credentials, cookies, or exception messages into TaskRuns.

Disable `CN_FUND_INDEX_PIPELINE_ENABLED` to stop scheduled runs without deleting stored data.
