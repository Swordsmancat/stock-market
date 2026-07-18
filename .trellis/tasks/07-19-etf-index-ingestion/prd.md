# ETF and Index Ingestion PRD

> Created: 2026-07-19
> Status: Planning

## Goal

Populate the existing ETF and index K-line workspaces with durable, provider-attributed CN market data through one automatic, observable ingestion pipeline. The feature should remove the current zero-catalog storage gap without adding trading behavior or provider calls to read pages.

## Background

- The 2026-07-19 real-data usability acceptance found 0 stored ETF instruments and 0 stored index instruments.
- The unified K-line read API and Web pages already support `stock`, `etf`, and `index` identities and remain database-only.
- Existing ingestion already provides TaskRun-backed stock universe sync and single/batch daily-bar jobs, but universe reconciliation is stock-only and daily-bar routing does not support index-specific provider methods.
- `AkShareProvider` already contains normalized index daily-bar support; ETF/index directory discovery and end-to-end orchestration are missing.

## Requirements

### R1. Asset-specific provider catalogs

- AkShare must expose normalized CN `etf` and `index` universe snapshots in addition to the existing `stock` snapshot.
- Every accepted identity must include symbol, non-empty name, market `CN`, exchange, asset type, currency, provider, source, timestamp, completeness, availability, and bounded diagnostics.
- Invalid and duplicate rows must be skipped or deduplicated deterministically without storing raw provider payloads.

### R2. Compatible universe persistence

- Universe sync must accept only `stock`, `etf`, or `index`, defaulting to `stock` for existing callers.
- Reconciliation, activation, and deactivation must be isolated by asset type so one catalog cannot deactivate another.
- Instrument identity must allow the same CN symbol to coexist across different asset types while remaining unique within one asset type.
- Failed or incomplete refreshes must preserve the last good active catalog.
- Sync history and status projections must identify the asset type. Existing sync rows migrate as `stock`.

### R3. Asset-aware daily bars

- ETF daily bars must use an ETF-capable AkShare source and index daily bars must use the existing index-specific provider boundary.
- Stored bars must retain effective provider, source, adjustment, priority, and ingestion timestamp.
- Existing stock ingestion behavior and public signatures remain compatible.

### R4. Automatic bounded pipeline

- One Celery task must sequentially sync ETF then index catalogs and ingest a bounded recent daily-bar window for their active instruments.
- The task must reject overlapping fresh runs, update TaskRun progress, expose per-asset catalog/bar counts and sanitized diagnostics, and fail on provider-wide failure while retaining earlier committed checkpoints.
- Celery Beat must schedule the pipeline after the CN trading day. Direct manual/API dispatch must use the same task and TaskRun lifecycle.
- External calls remain sequential and rate-limited; no fan-out task storm is allowed.

### R5. Existing observability and UI compatibility

- The crawler monitor must recognize the new task as a curated collection pipeline.
- Existing storage and unified K-line pages should begin showing real stored ETF/index coverage without page-specific write behavior or live fallbacks.

## Acceptance Criteria

- [ ] Provider tests prove ETF/index schema normalization, identity mapping, deterministic dedupe, and unavailable diagnostics.
- [ ] Service tests prove asset-type-isolated sync, last-good preservation, status projection, and stock backward compatibility.
- [ ] Daily-bar tests prove ETF and index route to the correct source and persist provenance.
- [ ] Worker, dispatcher, API, schedule, and crawler-monitor tests prove one observable pipeline, overlap suppression, progress, and bounded input.
- [ ] Migration tests prove existing sync rows become `stock`, the new asset type is queryable, and `(market, symbol, asset_type)` identity permits legitimate stock/index symbol overlap.
- [ ] Focused backend tests and the relevant full test suite pass.
- [ ] A live local run stores non-zero ETF and index catalogs plus at least one coherent recent K-line for each type, or records a sanitized provider-wide blocker without fabricating data.
- [ ] Normal Web/API services on ports 3000/8000 remain available during validation.

## Out of Scope

- Trading, orders, portfolio automation, or recommendations.
- Logged-in Eastmoney sessions, browser cookies, CAPTCHA bypass, or private endpoints.
- Page-load provider calls, bar stitching across incompatible adjustments, or fabricated fallback rows.
- HK/US ETF or index catalogs, intraday bars, constituents, fund NAV, or index fundamentals.
- Redesigning the existing K-line or storage pages.
