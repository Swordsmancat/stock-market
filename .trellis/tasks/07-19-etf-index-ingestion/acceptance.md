# ETF and Index Ingestion Acceptance

## Runtime

- Date: 2026-07-19 Asia/Shanghai
- Normal Web: `http://127.0.0.1:3000/zh/storage` returned 200 throughout.
- Normal API: `http://127.0.0.1:8000/health` returned 200 throughout.
- Migration head: `0028_etf_index_universe_identity`.
- Worker registered `ingestion.sync_cn_fund_index_data`; Beat started normally.

## Bounded Runs

Both runs used `lookback_days=120` and `max_symbols_per_type=3`.

1. TaskRun `99588801-5673-4fdd-a1a5-1edecd0896de` preserved both catalogs, then stopped with `CN_ETF_DAILY_BARS_PROVIDER_WIDE_FAILURE`. Direct probing confirmed the Eastmoney ETF history endpoint was closing public connections.
2. After adding the explicit Sina ETF daily fallback, TaskRun `396eb5f5-b003-41f2-aae7-822e62178e97` succeeded with `status=ok`.

## Stored Evidence

| Asset | Active catalog | Effective catalog source | Sampled instruments | Stored bars | Bar source | Adjustment |
| --- | ---: | --- | ---: | ---: | --- | --- |
| ETF | 1,549 | `akshare.fund_etf_spot_em` | 3 | 240 | `akshare.fund_etf_hist_sina` | `raw` |
| Index | 550 | `akshare.stock_zh_index_spot_sina` | 3 | 240 | `akshare.stock_zh_index_daily` | `raw` |

The index snapshot was degraded only because 12 of 562 Sina directory rows had unsupported identities; 550 valid rows were stored. The snapshot includes `INSTRUMENT_UNIVERSE_FALLBACK_USED` and does not contain raw provider error text.

ETF samples `159001`, `159003`, and `159005` each stored 80 bars from 2026-03-23 through 2026-07-17 with source priority 1. Index samples `000001`, `000002`, and `000003` each stored 80 bars for the same range with source priority 0.

## Read Acceptance

- ETF API: `/instrument-kline?asset_type=etf&symbol=159001&market=CN&period=3m` returned database-backed `status=ready` with a stored series.
- Index API: `/instrument-kline?asset_type=index&symbol=000001&market=CN&period=3m` returned database-backed `status=ready` with a stored series.
- Both localized K-line pages returned 200.
- Read payload safety remained `no_provider_request=true`; no page-specific refresh or live fallback was added.
