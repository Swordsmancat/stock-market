# ETF and Index Ingestion Design

## Boundaries

The change extends the existing provider -> service -> worker -> TaskRun path. Read pages and read APIs remain unchanged and database-only.

## Provider Contracts

`AkShareProvider.fetch_instrument_universe(market, asset_type="stock")` selects one injected downloader and one normalizer:

- `stock`: `stock_info_a_code_name` (existing behavior)
- `etf`: `fund_etf_spot_em`
- `index`: `stock_zh_index_spot_em`, with whole-snapshot fallback to `stock_zh_index_spot_sina`

Each normalizer returns `ProviderInstrumentUniverseSnapshot`. Symbols are normalized to six digits, names must be present, exchange identity is derived from provider market fields when available and from validated CN symbol conventions otherwise, and provider diagnostics contain only stable codes/counts.

Daily-bar coordination becomes asset aware:

- stock: existing resilient stock sources
- etf: primary `fund_etf_hist_em` (`qfq`), then `fund_etf_hist_sina` (`raw`) as a whole-request fallback
- index: `AkShareProvider.fetch_index_bars` with raw adjustment metadata

The coordinator remains responsible for sequential rate limiting and source-attempt metadata. It selects one source per request and never stitches incompatible adjustments.

## Persistence

`instrument_universe_syncs.asset_type` is added as non-null `stock` with an index supporting `(market, provider, asset_type, created_at)` status lookup. The service filters existing instruments, managed rows, latest sync, reconciliation, and deactivation by asset type.

No new instrument or daily-bar table is needed. The instrument uniqueness constraint changes from `(market_id, symbol)` to `(market_id, symbol, asset_type)` because CN stocks and indices legitimately reuse codes such as `000001`. Existing `DailyBar` composite identity and provenance fields remain authoritative. Service lookups include asset type so a catalog never mutates a different identity.

## Pipeline

`ingestion.sync_cn_fund_index_data` owns one worker session and one TaskRun. It:

1. rejects a second fresh running instance when invoked directly;
2. syncs the ETF catalog, then the index catalog;
3. queries active stored instruments for each asset type;
4. ingests a bounded recent daily-bar window sequentially using the existing service;
5. checkpoints each symbol through service-owned commits and records progress;
6. reports bounded per-type counts, source distribution, and diagnostic codes.

The job does not enqueue child Celery tasks. Provider-wide failure for an asset type is terminal for the run, while rows committed before the failure remain valid and observable. A later run idempotently resumes through upserts.

Beat runs once on CN weekdays after market close. An API route enqueues the same task for explicit manual operation. Generic task retry/dispatch uses the same task name and payload.

## Compatibility

- Existing universe sync calls default to `stock`.
- Existing stock schedules and stock bar sources are unchanged.
- Existing universe-sync rows migrate to `asset_type=stock`; existing instrument rows retain their current asset type while the uniqueness constraint becomes asset aware.
- Read endpoints and Web components receive no contract changes.

## Safety and Rollback

- External calls are public, Cookie-free, sequential, and rate limited.
- TaskRun inputs/results exclude keys, raw responses, environment values, and credential URLs.
- Disable the new Beat entry to stop automatic collection.
- Downgrade removes only the sync-history asset column/index; instrument and bar data remain ordinary existing rows and can be retained.
