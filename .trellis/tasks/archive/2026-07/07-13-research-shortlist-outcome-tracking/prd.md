# Research shortlist outcome tracking

## Goal

Close the most important feedback gap in the A-share AI Research workflow:
show what happened after each immutable daily shortlist candidate was published.
The feature records and presents strict 5/20/60-session outcomes so the user can
judge the research process from evidence instead of adding more data plumbing or
treating an AI explanation as proof of quality.

This remains a personal research signal review. It does not backtest a
portfolio, recommend a trade, or change shortlist membership, rank, or weights.

## Background

- Daily shortlist runs and candidates are already persisted with a frozen
  decision-date close and provenance.
- The current product cannot answer whether a published candidate later rose,
  fell, or underperformed the market.
- Existing recommendation evaluators are response-only and align benchmark
  series by array position. They cannot satisfy point-in-time cohort accounting.
- `DailyBar` is the only V1 price ledger. Its rows may later be replaced by an
  equal- or higher-priority source, so terminal outcome values and provenance
  must be frozen independently.
- The existing stock symbol `000300` cannot safely identify CSI 300. Outcome
  tracking uses a dedicated local index instrument instead.

## Requirements

### R1. Strict candidate horizons

- Track fixed horizons of 5, 20, and 60 sessions for every saved candidate.
- Horizon N matures on the Nth distinct local `DailyBar` strictly after the
  candidate's frozen entry trade date and no later than the evaluation cutoff.
- The entry day does not count. Weekends, holidays, and suspension days with no
  candidate bar do not count.
- Before N bars exist, the public state is `pending` and includes the available
  forward-bar count. Missing values remain `null`; they are never filled with
  zero.
- If N bars exist but no terminal evaluation has been committed, a read remains
  `pending`, caps progress at `N/N`, and sets `ready_for_evaluation=true`.
  Reads do not publish unfrozen metrics as a substitute for explicit evaluation.
- Once N bars exist, calculate `return_ratio = exit_close / entry_close - 1`
  and `drawdown_ratio = min(0, min(low_1..low_N) / entry_close - 1)`.

### R2. Local, completed-day evidence only

- Evaluation reads `DailyBar` directly and must not call a provider, fallback,
  market-data payload service, or network client.
- Every invocation has an explicit effective `as_of` cutoff. Future and
  incomplete A-share trading dates are rejected.
- A historical read shows a stored terminal observation only when its frozen
  maturity date is no later than the requested `as_of`; otherwise that horizon
  is reconstructed as pending from bars through the cutoff. Later evaluation
  time alone must not leak a post-cutoff result into the read.
- Manual invocation uses a conservative Asia/Shanghai completed-day default;
  the later automation task may supply a verified daily-bar watermark.
- The browser/API cannot assert a trusted watermark. A future internal worker
  may supply `verified_completed_through` to the same service; current-day use
  additionally requires local time at or after 16:00 and never bypasses the
  per-bar completion rule.
- A stored bar counts only when its `ingested_at` is at or after 16:00
  Asia/Shanghai on its own trade date, or on a later local date. An intraday row
  that was never refreshed remains incomplete even on the next calendar day and
  cannot mature a horizon.
- Bars after `as_of` and bars after the Nth forward observation cannot affect a
  terminal result.

### R3. Frozen and auditable terminal observations

- Persist only terminal candidate states, `evaluated` or `blocked`; derive
  `pending` from the frozen candidate and current local bars.
- Freeze the maturity date, exit close, minimum forward low, result ratios, and
  source provenance under a versioned methodology.
- Repeated or concurrent evaluation must return the same terminal candidate
  observation and must not create duplicates.
- A later source replacement must not silently rewrite a terminal result.
- At maturity, the current entry bar must still match the frozen entry close and
  adjustment basis. Unknown or incompatible adjustments and invalid prices
  produce a structured terminal `blocked` state rather than a fabricated
  metric.
- Canonical known adjustments are `qfq`, `hfq`, and `raw` (including explicit
  raw aliases). Blank, `unknown`, `legacy_unknown`, and `provider_default` are
  not evidence of a compatible basis and fail closed.
- The known legacy provenance defect where `tushare.pro.daily` raw prices were
  labeled `qfq` must be corrected for future ingestion and normalized to raw
  during outcome evaluation of existing rows. A path mixing that effective raw
  series with AkShare qfq remains incompatible.
- Different providers or sources are allowed when the adjustment basis and
  frozen entry value remain compatible.
- Inactive or later-delisted instruments remain in their original cohort and in
  every aggregate denominator.

### R4. Date-aligned CSI 300 comparison

- The benchmark is the local canonical instrument with
  `market=CN`, `asset_type=index`, and `symbol=cn_csi_300`.
- Never resolve the benchmark from the CN stock symbol `000300`, and never
  create or fetch a benchmark implicitly during outcome evaluation.
- Benchmark return requires valid local bars on the candidate's exact entry and
  maturity dates. A neighboring or same-position bar is not a substitute.
- Missing benchmark data does not block an otherwise valid candidate result.
  Benchmark status and sample size are independent; relative metrics remain
  `null` with a structured diagnostic.
- A missing benchmark observation may be filled once when the exact local bars
  later become available. Evaluated or blocked benchmark observations remain
  immutable without a future explicit revision workflow.

### R5. Cohort read model and manual evaluation

- Add an idempotent manual evaluation endpoint for one shortlist run.
- Add a stable outcome detail endpoint for one run and a tracking endpoint that
  returns the latest cohort plus paginated recent cohort aggregates.
- Tracking history is limited to the same A-share shortlist market/profile
  scope with `limit` defaulting to 10 and constrained to `1..50`; it is not a
  general backtest or export endpoint.
- Keep existing generate/latest/detail shortlist contracts unchanged so an
  outcome failure cannot make the daily shortlist unavailable.
- For every horizon expose total, evaluated, pending, and blocked counts;
  absolute-return sample size; benchmark sample size; positive-return ratio;
  mean and median return; mean drawdown; and mean excess return.
- For every horizon,
  `total_count = evaluated_count + pending_count + blocked_count`.
- Aggregate metrics with no observations remain `null`.

### R6. AI Research presentation

- Add an independently degradable outcome panel immediately after the daily
  shortlist and before the existing AI Research Desk.
- Show a compact 5D/20D/60D cohort summary, the current candidate-by-horizon
  matrix, and recent cohort history.
- `pending` shows available/N bars; `evaluated` shows absolute return,
  drawdown, and benchmark-relative return when available; `blocked` shows a
  localized structured code.
- Provide an update-results command that calls the same backend evaluation
  service later reused by automation.
- When a new daily shortlist is generated and the page refreshes, the outcome
  panel must switch to the same new run rather than retaining client state from
  the previous cohort.
- Backend free-form diagnostic text must not leak across locales. An outcome
  load or update failure is local to this panel.

### R7. Safety and product focus

- Every payload and surface retains `research_signal_only=true` and explicit
  non-advice wording.
- Do not emit buy/sell/hold actions, target prices, position sizes, portfolio
  weights, order intent, broker routing, or automated execution.
- Outcome data must not automatically alter scoring rules, candidate rank, or
  future shortlist membership.

## Acceptance Criteria

- [x] 4/5, 19/20, and 59/60 forward-bar boundaries remain not-ready pending;
      the required candidate bar changes the read state to ready pending N/N,
      and explicit evaluation then materializes one terminal observation.
- [x] Entry-day, post-cutoff, and N+1 bars are excluded; suspension gaps count
      no sessions; full-up paths report zero drawdown and intermediate lows are
      measured correctly.
- [x] A prior-day row last ingested before 16:00 local remains excluded after
      midnight; a post-16:00 or later-date ingestion becomes eligible with UTC
      and Asia/Shanghai boundaries tested.
- [x] Invalid prices, revised entry bars, unknown adjustments, and adjustment
      mismatches become structured blocked outcomes with null metrics.
- [x] A GET before first evaluation returns pending `N/N` plus
      `ready_for_evaluation=true`, without calculating or exposing unfrozen
      ratios; the POST then commits exactly one terminal result.
- [x] A same-adjustment path may span different providers/sources, while a
      terminal result is unchanged by later source replacement or repeated
      evaluation.
- [x] Tushare `pro.daily` is treated and newly written as raw; mixing its
      effective raw path with qfq blocks rather than producing a false return.
- [x] CSI 300 joins exact entry/maturity dates through only `cn_csi_300` index
      identity; stock `000300` is never accepted as the benchmark.
- [x] Missing benchmark data preserves the evaluated candidate return and null
      relative metrics, and later exact local bars can fill the benchmark once.
- [x] Detail and tracking responses expose all candidates and horizons,
      preserve inactive members, satisfy count identities, and never convert
      missing metrics to zero.
- [x] Historical `as_of` reads hide terminal observations whose maturity date
      is after the cutoff and derive the correct earlier pending progress.
- [x] Evaluation uses a bounded number of bulk database queries for a full
      shortlist and performs no provider/network fallback.
- [x] The localized, responsive panel supports loaded, pending, evaluated,
      blocked, no-data, update, and isolated-error states without changing the
      existing shortlist contract or disabling the rest of AI Research.
- [x] Generating a new shortlist remounts or synchronizes outcome state by run
      ID so shortlist and outcome panels cannot display different cohorts.
- [x] Migration upgrade/downgrade, focused and full backend/frontend suites,
      type checking, lint, localization, Trellis validation, and browser QA pass.
- [x] Normal ports 3000/8000 remain compatible and no output introduces trading
      instructions or claims of predictive alpha.

## Out of Scope

- Portfolio backtesting, transaction costs, slippage, position sizing, P&L, or
  order execution.
- Retrofitting historical cohorts that were never published point in time.
- Automatically learning or optimizing shortlist thresholds or weights.
- New provider endpoints, network data repair, benchmark instrument creation,
  and historical bar rewrites. The narrow correction of existing Tushare
  `pro.daily` adjustment metadata for future writes is explicitly in scope.
- Corporate-action factor-vintage storage or automatic revision of a frozen
  outcome; V1 documents the remaining qfq proxy risk and fails closed when the
  frozen entry no longer matches.
- Scheduling and watermark orchestration, which belong to the next child task.
