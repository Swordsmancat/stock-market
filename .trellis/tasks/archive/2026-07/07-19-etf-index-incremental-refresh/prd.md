# ETF and Index Incremental Refresh PRD

> Created: 2026-07-19
> Status: Planning

## Goal

Reduce the daily CN ETF/index refresh cost after the initial 100% catalog backfill while preserving coherent daily-bar provenance and automatically seeding newly discovered instruments.

## Background

- The first complete run succeeded for 1,549 ETFs and 550 indexes but took about 33 minutes and rewrote a 120-day window for every instrument.
- Existing ETF evidence is coherent per instrument: 1,545 instruments use `akshare.fund_etf_hist_sina/raw` and four use `akshare.fund_etf_hist_em/qfq`.
- The K-line reader selects one provider/adjustment cohort. Incremental writes from a different adjustment could therefore create stored mixed cohorts and hide the newest bars from the selected series.
- The pipeline already commits each symbol independently, rate limits sequentially, exposes TaskRun progress, and preserves provider provenance.

## Requirements

### R1. Per-instrument refresh windows

- Scheduled runs must use incremental windows; manual API runs must preserve the requested full window.
- For an instrument with no stored daily bars, request the full pipeline lookback window.
- For an instrument with stored bars older than the requested end date, request from the later of the global start and seven calendar days before its latest stored date.
- For an instrument already stored through the requested end date, make no provider call and record it as current.
- Window selection must be computed from one bounded database projection rather than one query per symbol.

### R2. Provenance-locked incremental updates

- Existing ETF instruments must refresh from their latest stored source and adjustment only.
- `fund_etf_hist_sina/raw` and `fund_etf_hist_em/qfq` must never be used as cross-adjustment fallbacks for an existing instrument.
- New ETF instruments without bars retain the current resilient Eastmoney-then-Sina seed behavior.
- Existing index instruments continue using `stock_zh_index_daily/raw`.
- An unrecognized stored source must fail that symbol with a sanitized diagnostic rather than silently switching provenance.

### R3. Observable compatibility

- Keep the worker name, API signature, Beat schedule, overlap protection, sequential pacing, and existing full-lookback input compatible.
- Derive refresh mode from the existing `trigger`: `scheduled` is incremental and `manual` is full-window.
- Extend result metadata with fixed overlap days and per-asset counts for full seed, incremental refresh, and already-current skips.
- Provider-wide failure applies only when at least one symbol was attempted and none were ingested; an all-current run succeeds without provider calls.
- Missing/no-data/failed symbol behavior and earlier committed checkpoints remain unchanged.

## Acceptance Criteria

- [ ] Service tests prove full seeding for missing bars, seven-day overlap for existing bars, and zero provider calls for current instruments.
- [ ] Worker tests prove scheduled delivery selects incremental mode while manual dispatch preserves full-window mode.
- [ ] Tests prove existing ETF source/adjustment is locked and new ETFs retain resilient fallback.
- [ ] Tests prove all-current runs succeed and attempted provider-wide failures remain terminal and secret-safe.
- [ ] Result payload reports `overlap_days`, `full_seed`, `incremental`, and `current` counts per asset.
- [ ] Existing provider, worker, API, schedule, crawler-monitor, and K-line tests remain green.
- [ ] A bounded runtime rerun after the complete baseline processes current data without corrupting source/adjustment cohorts; ports 3000/8000 remain available.

## Out of Scope

- Adding user-facing configuration for overlap days.
- Changing catalog sources, bar schemas, schedules, or K-line read behavior.
- Deleting or rewriting historical bars to migrate between adjustment cohorts.
- Parallel provider fan-out, trading, logged-in sessions, cookies, or page-load refreshes.
