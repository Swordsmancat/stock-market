# Repair personal A-share evidence readiness

## Goal

Make the existing personal daily A-share research loop usable with the current
full-market universe, without adding product surfaces, provider abstractions,
portfolio features, or lower evidence standards.

## Background

- The first authoritative AkShare universe sync completed at 06:30
  Asia/Shanghai on 2026-07-14. It reconciled the three legacy CN stocks in
  place and expanded the active universe to 5,530 stocks: SSE 2,308, SZSE
  2,895, BSE 327, and UNKNOWN 0.
- The earlier 2/3 UNKNOWN result is historical. Current readiness is daily bars
  2/5,530, technical indicators 2/5,530, and fundamentals 3/5,530.
- All existing backfills froze their three-symbol scope before the universe
  sync. A daily ten-day incremental cannot bootstrap the new instruments to
  the 35-bar readiness minimum.
- The strict AkShare Eastmoney daily endpoint currently disconnects. Existing
  `cn_resilient` fallback probes succeeded for representative SSE, SZSE, and
  current 92-prefix BSE stocks through `akshare.stock_zh_a_daily`.
- The weekday 18:30 incremental schedule does not currently pass
  `daily_bar_policy`, so it still defaults to `strict`.
- Nine `legacy_unknown` weekend/test bars remain on 600519 and can contaminate
  local indicator windows.

## Requirements

### R1. Preserve the authoritative universe repair

- Add a regression proving universe sync repairs a matching legacy six-digit
  CN stock with null exchange/provider metadata in place.
- Do not add another exchange inference path or manually resync the universe.

### R2. Use the existing resilient daily-bar policy by default

- Pass `daily_bar_policy="cn_resilient"` from the existing weekday 18:30
  incremental Beat entry.
- Keep fixed source order, provenance, circuit breakers, pacing, diagnostics,
  and canonical priority behavior unchanged.
- Do not add a provider or lower any threshold.

### R3. Perform one bounded bootstrap on the normal local database

- Use the last completed trading date, 2026-07-13, as the fixed end date.
- Remove only the nine proven `600519` `legacy_unknown` test rows, with the
  exact symbol/source/count verified immediately before deletion.
- Run a 50-symbol, daily-bars-only `cn_resilient` canary first. Continue only
  if at least 48 succeed, retry has at most two symbols, and all three
  exchanges have usable evidence.
- Then run one full-market daily-bars baseline, one local-only technical
  indicator baseline, and fundamental shards 0 through 4 sequentially.
- At every POST boundary require no active CN/AkShare backfill. Keep only one
  AkShare backfill active at any time and preserve checkpoints on failure.
- Cancel and retain evidence if a provider-wide schema, rate, or source failure
  makes the threshold impossible; do not fabricate success.

### R4. Restore the existing publication gate

- Daily bars must pass 95%, technical indicators 90%, fundamentals 80%, and
  SSE/SZSE/BSE representation must remain nonzero.
- After readiness, run the existing daily research task and require a trusted
  watermark plus created/reused shortlist behavior.
- Keep deterministic ranking, immutable outcomes, TaskRun lineage, and all
  research-only/no-trading boundaries unchanged.

### R5. Keep the personal product simple

- Add no page, dashboard, account role, scheduler control, personal-universe
  model, strategy optimizer, or trading behavior.
- Reuse existing API, TaskRun, coverage, and AI Research surfaces.

## Acceptance Criteria

- [x] Legacy null-exchange CN stock reconciliation is covered by a focused test.
- [x] The weekday incremental schedule explicitly uses `cn_resilient` and its
      focused schedule test passes.
- [x] The nine proven synthetic 600519 rows are removed without touching
      provider-attributed bars.
- [x] The 50-symbol canary meets its success, retry, and three-exchange gates.
- [x] Full daily bars pass 95% with SSE/SZSE/BSE evidence.
- [x] Local technical indicators pass 90%.
- [x] Sequential fundamental shards pass 80%.
- [x] The daily research loop reaches a trusted watermark and creates or reuses
      an immutable shortlist without provider access inside the loop.
- [x] Normal 3000/8000 services remain healthy; focused/full tests, Ruff,
      Trellis validation, and `git diff --check` pass.
- [x] No new product surface or trading/portfolio behavior is introduced.

## Out of Scope

- Restricting the active universe to a watchlist or personal subset.
- New data providers, parallel provider fan-out, or relaxed readiness gates.
- Backtesting, optimization, portfolios, orders, brokers, or execution.
- UI redesign or a new operations dashboard.
