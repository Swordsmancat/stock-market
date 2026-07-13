# Persisted daily research shortlist

## Goal

Publish the first trustworthy daily A-share research shortlist: a persisted,
idempotent snapshot with meaningful deterministic ranking, structured evidence
for and against each candidate, visible gaps/invalidation conditions, and a
primary comparison surface in the existing AI Research page.

This child establishes the frozen cohort and entry observation required by the
later 5/20/60 outcome task. It does not calculate outcomes or schedule itself.

## Requirements

### R1. Current-day publication only

- Generate from locally stored active `CN` `stock` instruments only.
- Derive the decision date from the latest stored in-scope daily bar. Do not
  accept an arbitrary historical date in V1.
- Before publication, reuse existing evidence-coverage thresholds (95% daily
  bars, 90% critical technical indicators, 80% complete fundamentals and all
  three A-share exchanges represented) as the readiness gate.
- A published candidate's entry bar must be exactly on the decision date.
  Stale bars are excluded and diagnosed.
- Generation must not call a live market/news/provider boundary.

### R2. Eligibility and score are separate

- Reuse the selected visible profile and overrides as all-or-nothing eligibility
  gates. Missing required evidence remains a non-match.
- Score all eligible, decision-date-aligned candidates with the versioned
  `daily_research_score_v1` contract before applying the requested shortlist
  limit (`1..20`).
- The score must be in `[0, 1]`, include visible dimension/rule contributions,
  and produce deterministic order by total score descending, minimum rule
  buffer descending, then symbol ascending.
- AI text, disclosures, market events, and uncited prose have zero numeric
  influence. AI cannot alter membership or rank.
- Keep the existing `/stock-selection/screen` and `/discover` behavior backward
  compatible; the new published-resource payload owns the new score semantics.

### R3. Candidate decision record

Each saved candidate must include:

- symbol/name/market/instrument identity and rank;
- total score, active dimension weights, and per-rule buffer/contribution;
- up to three strongest supporting factors and up to two weakest/opposing
  factors when a weak buffer exists;
- structured data/freshness gaps and all rule-derived invalidation conditions;
- entry trade date/close plus provider/source/adjustment/source-priority and
  ingestion timestamp snapshots;
- matched rules, evidence snapshot, allowed citation IDs, and research-only
  safety metadata.

### R4. Immutable persistence and idempotency

- Add dedicated shortlist-run and shortlist-candidate tables.
- The generation key must be a canonical hash of market, asset type, profile,
  effective criteria, decision date, scoring version, and shortlist limit.
- Repeating the same generation request returns the existing committed run and
  does not call the LLM or duplicate candidates.
- Persist the run and every candidate in one transaction. A failure must leave
  neither a partial published run nor orphan candidates.
- Existing `ResearchBrief`, `GeneratedReport`, watchlist, portfolio, and
  `TaskRun.result_json` storage must not be repurposed.

### R5. APIs

- `POST /research-shortlists/generate` accepts profile, overrides, market,
  asset type, shortlist limit, locale, and `use_llm` fields compatible with the
  existing discovery workflow.
- `GET /research-shortlists/latest?market=CN&profile_id=balanced_research`
  returns the latest matching committed run or an explicit no-data payload.
- `GET /research-shortlists/{run_id}` returns one committed run or HTTP 404.
- Responses expose decision/generation lineage, structured candidates,
  coverage/diagnostics, explanation/model/citations/safety, and
  `research_signal_only=true`.

### R6. AI Research first-screen workflow

- Add a localized daily-shortlist panel as the first section of
  `/[locale]/ai-research`.
- The page server-loads the latest snapshot as an optional dependency. Failure
  or absence must not prevent the existing research desk from rendering.
- Show decision date, generation time, profile/status, evaluated/matched/returned
  counts, evidence readiness, score, positive/opposing factors, gaps,
  invalidation condition, and evidence count in a compact comparison.
- Each row links to `/instruments/{symbol}?research_snapshot_id={run_id}` and may
  also use the existing in-page symbol handoff.
- Move evidence coverage and manual discovery below the daily shortlist and
  research desk; keep their behavior intact.

### R7. Safety and language

- New user-facing copy is localized in English and Chinese.
- Responses and UI retain research-only/non-advice/no-automated-trading wording.
- Do not introduce buy/sell/hold, target-price, sizing, portfolio allocation,
  order, broker, or execution semantics.

## Acceptance Criteria

- [x] Ready local evidence produces one committed shortlist run and bounded,
      uniquely ranked candidates with at least two different fixture scores.
- [x] Repeating the canonical request returns the same run ID and candidate rows
      without invoking the explanation provider again.
- [x] Insufficient coverage, no in-scope bars, and stale candidate bars fail
      closed with diagnostics and no partial database writes.
- [x] Candidate payloads contain score decomposition, structured supporting and
      opposing factors, gaps, invalidation conditions, frozen entry provenance,
      citations, and safety metadata.
- [x] AI failure or unknown symbol/citation falls back deterministically without
      changing saved membership or rank.
- [x] Latest/detail APIs and Next proxies preserve status codes, no-store
      behavior, request fields, and explicit no-data/404 behavior.
- [x] `/ai-research` renders the persisted latest shortlist first, survives
      refresh, links to instrument deep analysis, and remains usable when the
      latest request fails.
- [x] Existing stock-selection/discovery tests remain compatible.
- [x] Migration upgrade/downgrade, focused tests, full backend/frontend tests,
      Ruff, TypeScript, locale JSON, Trellis validation, and `git diff --check`
      pass.

## Out of Scope

- 5/20/60 outcome records or cohort performance metrics.
- Celery/Beat scheduling, automatic daily publication, or TaskRun operations.
- Historical shortlist reconstruction.
- Numeric scoring from disclosures, market events, LLM prose, or new providers.
- Changes to Evidence Center, instrument analysis contracts, or report storage.
