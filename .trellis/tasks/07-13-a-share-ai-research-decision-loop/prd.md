# A-share AI research decision loop

## Goal

Turn the existing A-share evidence, deterministic screening, and AI explanation
capabilities into one repeatable decision-support loop: each completed trading day
produces a small, transparent research shortlist; each candidate has supporting
and opposing evidence, data gaps, invalidation conditions, and a direct path to
deeper analysis; subsequent 5/20/60-trading-day outcomes are recorded and
compared with a date-aligned benchmark.

The product remains a personal research cockpit. It does not issue trading
instructions or automate investment decisions.

## Background

- The current `/stock-selection/discover` flow scans locally stored evidence and
  prevents AI from changing deterministic membership or order.
- The current shortlist is response-only and disappears on refresh.
- The current selector is an all-or-nothing gate. Every returned candidate has
  passed every active criterion, so its score is normally `1.0`; ties are then
  broken by symbol. This is not a meaningful daily ranking.
- Existing recommendation and strategy evaluators contain useful historical
  return formulas, but they are stateless and align benchmark bars by array
  position rather than exact trading date. They cannot be used as the outcome
  ledger without a new contract.
- The existing `/ai-research` route is already the primary research workspace;
  evidence coverage and manual screening currently appear before the actual
  research workflow.

## Requirements

### R1. Daily deterministic shortlist

- Generate a bounded A-share research shortlist from locally stored evidence
  after a completed market day.
- Keep explicit profile thresholds as eligibility/veto gates, then apply a
  separate, versioned, deterministic scoring model with visible factor weights
  and per-factor contributions.
- Ranking must be reproducible from the frozen input snapshot. AI may explain
  the result but may not add, remove, or reorder candidates.
- Missing, stale, or misaligned evidence must reduce coverage or block a
  candidate; it must never be imputed as a favorable value.

### R2. Decision-oriented candidate record

Each candidate must expose:

- rank and total score;
- factor score decomposition;
- supporting factors and opposing factors;
- material data gaps and evidence freshness;
- explicit invalidation conditions derived from the deterministic rules;
- frozen entry observation date/close and source provenance;
- evidence citation identifiers and the research-only safety boundary.

Official disclosures and market-daily evidence may initially be attached as
citable context. They must not receive numeric score weight until a reviewed,
deterministic mapping exists.

### R3. Immutable and queryable snapshots

- Persist shortlist runs and candidates in dedicated domain tables rather than
  `TaskRun.result_json`, `ResearchBrief`, `GeneratedReport`, watchlists, or
  portfolios.
- A generation key must make retries idempotent for the same market, profile,
  decision date, rule/scoring version, and criteria snapshot.
- Expose latest and detail/history retrieval so a page refresh returns the same
  published snapshot and lineage.
- V1 starts tracking from newly generated snapshots. It must not fabricate
  historical shortlists from today's evidence.

### R4. Primary AI Research workflow

- Show the latest persisted daily shortlist as the first work surface on the
  existing `/ai-research` page.
- Show snapshot date/status/coverage and a compact candidate comparison before
  infrastructure and manual tuning controls.
- Each candidate must link to the existing `/instruments/{symbol}` deep-analysis
  view and may also hand off the symbol to the existing in-page research desk.
- Evidence coverage and manual full-market screening remain available as
  secondary data-preparation tools.

### R5. Outcome tracking

- Persist 5/20/60-trading-day observations for each saved candidate.
- Horizon N means the Nth distinct stored daily bar strictly after the frozen
  entry trade date, not N calendar days.
- Before explicit evaluation, a horizon with N available bars remains a visible
  pending `N/N` read state marked ready; evaluation materializes exactly one
  immutable evaluated or blocked terminal observation.
- Store absolute return, future low-based drawdown, and benchmark-relative
  return when exact-date benchmark bars exist.
- Pending, evaluated, and blocked counts and sample sizes must remain visible;
  missing values must remain null with diagnostics rather than becoming zero.
- Later delisting or removal from the active universe must not remove a saved
  candidate from outcome aggregates.

### R6. Daily operation

- The same generation and outcome services must support manual invocation and
  scheduled TaskRun/Celery execution.
- Scheduled generation runs only after the local A-share daily-bar watermark is
  complete enough for the decision date.
- Retries must be idempotent and must not silently revise published entry or
  outcome observations after later source replacement.

### R7. Safety and product focus

- All surfaces must retain `research_signal_only=true` and explicit non-advice
  wording.
- Do not emit buy/sell/hold actions, target prices, position sizes, order
  intents, portfolio weights, broker routing, or automated execution.
- New provider integrations, OCR/vector search, and unrelated evidence
  infrastructure are out of scope unless they directly block this loop.

## Task Map

1. `daily-research-shortlist-snapshot`: meaningful deterministic score,
   immutable run/item persistence, latest/detail APIs, and the primary
   `/ai-research` shortlist panel.
2. `research-shortlist-outcome-tracking`: candidate tracking ledger and strict
   5/20/60-trading-day, date-aligned CSI 300 outcome observations.
3. `daily-research-loop-automation`: TaskRun/Celery scheduling, watermark
   gating, outcome maturation, and end-to-end operational acceptance.

The children are executed in this order. The parent owns only the source
requirements and final integration acceptance.

## Acceptance Criteria

- [ ] A completed A-share trading day can produce one idempotent, persisted,
      versioned shortlist whose candidates do not all collapse to score `1.0`.
- [ ] Every saved candidate contains reproducible score factors, positive and
      opposing evidence, gaps, invalidation conditions, entry observation, and
      citations without AI-controlled membership or rank.
- [ ] Opening or refreshing `/ai-research` shows the latest persisted shortlist
      first and links every candidate to existing deep analysis.
- [ ] 5/20/60 data readiness occurs only on the corresponding stored trading
      bar; before evaluation a ready horizon stays pending `N/N`, and terminal
      results use exact-date CSI 300 alignment while incomplete evidence stays
      pending/null.
- [ ] Outcome aggregates show evaluated/pending/blocked counts and sample size,
      and retain inactive/delisted cohort members.
- [ ] Manual and scheduled runs share idempotent services, expose TaskRun
      lineage, and do not revise frozen published observations implicitly.
- [ ] Focused and full backend/frontend checks pass, migrations upgrade and
      downgrade cleanly, and the normal 3000/8000 runtime remains compatible.
- [ ] No output or UI introduces investment instructions or automated trading.

## Out of Scope

- Historical shortlist reconstruction without point-in-time evidence loaders.
- Portfolio simulation, transaction costs, slippage, order execution, or broker
  integration.
- Self-learning weights, parameter optimization, or claims of predictive alpha.
- New paid providers, new document corpora, OCR, embeddings, or vector search.
- Replacing the existing instrument assistant, Evidence Center, or reports.
