# A-share Multi-Provider Daily-Bar Resilience Design

## Architecture

```text
Backfill/API request (provider=akshare, daily_bar_policy)
  -> DailyBarFetchCoordinator
       strict       -> requested provider only
       cn_resilient -> AkShare Eastmoney -> AkShare Sina -> configured Tushare
  -> normalized + validated DailyBarFetchResult
  -> priority-aware canonical bars_1d upsert
  -> backfill source counters + coverage source distribution
  -> AI Research coverage panel
```

## Contracts

### Fetch result

A daily-bar fetch result owns:

- requested provider and policy
- effective provider, source endpoint, adjustment mode, and source priority
- normalized bars
- sanitized attempt diagnostics
- fallback-used and final status fields

The coordinator is the only owner of source ordering, eligibility, pacing, and circuit state. Provider adapters continue to normalize provider-specific frames.

### Policies

- `strict`: one source, no fallback, current service behavior.
- `cn_resilient`: fixed source chain; fallback is explicit in the persisted run request and result.

The fixed order is `akshare.stock_zh_a_hist` (Eastmoney), `akshare.stock_zh_a_daily` (Sina), and `tushare.pro.daily` when configured. Empty and classified provider failures may advance to the next eligible source. No provider is selected dynamically by popularity or availability.

### Canonical persistence

`bars_1d` gains nullable-safe/additive provenance columns populated as `legacy_unknown` for existing rows. Source priority is lower-is-better:

- 0: AkShare Eastmoney primary
- 1: AkShare Sina fallback
- 2: configured Tushare fallback
- 99: legacy/unknown

An upsert updates a row when the source is the same or the incoming priority is better. A worse source leaves the canonical row unchanged and reports a preserved-higher-priority count.

### Run state and coverage

`ResearchEvidenceBackfill` stores `daily_bar_policy` and `source_stats_json`. Resume/retry copies both. Coverage groups canonical rows by effective provider/source and reports row count plus distinct-instrument count; readiness thresholds remain unchanged.

## Provider Protection

- Calls remain sequential.
- Each source definition owns a minimum interval.
- A coordinator tracks consecutive failures and opens a run-local source circuit after three failures.
- A circuit-open primary is skipped for the rest of that execution, while a resumed run receives one fresh opportunity.
- Existing outer transient retry remains bounded; coordinator attempt diagnostics prevent failures from becoming silent no-data.

## Compatibility and Migration

- Existing callers omit `daily_bar_policy` and stay in `strict` mode.
- Existing bars remain queryable and are marked `legacy_unknown`.
- Existing coverage fields remain stable; source distribution and policy fields are additive.
- The migration is additive and reversible by dropping only the new columns.

## Rollout and Rollback

1. Add migration/domain fields and regression tests.
2. Add coordinator and Sina normalization behind explicit policy.
3. Integrate ingestion/backfill/API/worker and coverage.
4. Expose the explicit policy/source mix in AI Research.
5. Run a three-exchange canary before retrying the isolated full baseline.

Rollback disables `cn_resilient` callers first; strict ingestion remains available. Provenance columns are retained unless a separate schema rollback is explicitly required.
