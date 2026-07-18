# Production TaskRun shapes

- `ingestion.ingest_market_data` has successful CN/HK/US runs and uses `input_json.market` plus `provider`.
- `ingestion.sync_instrument_universe` records `market=CN`, `provider=akshare`, and completion progress.
- `ingestion.backfill_a_share_research_evidence` uses `run_kind=incremental` or `fundamental_shard`; the active fundamental shard exposed progress `675/1105` during planning.
- `ingestion.ingest_watchlist_official_disclosures` runs incrementally and has frequent successful TaskRuns.
- Report, research-loop, and alert TaskRuns exist but are not collection pipelines for this page.
- Existing TaskRun GET helpers call stale-run expiry. The monitor must query `TaskRun` directly so its read endpoint remains non-mutating.
