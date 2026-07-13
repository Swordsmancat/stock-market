# Persisted Daily Research Shortlist Contract

## Scenario: Immutable Point-in-Time A-share Research Cohort

### 1. Scope / Trigger

- Trigger: AI Research publishes a small daily A-share research cohort from
  locally stored evidence and later consumers need a frozen decision record.
- Scope: `ResearchShortlistRun` / `ResearchShortlistCandidate`, Alembic revisions
  `0020_research_shortlists` and `0022_research_shortlist_task_run`,
  `packages/services/research_shortlists.py`, the
  point-in-time selector and coverage gate, FastAPI/Next routes, and the first
  panel on `/[locale]/ai-research`.
- Non-goals: historical reconstruction, outcome calculation, scheduling,
  portfolio allocation, target prices, orders, brokers, or automated trading.

### 2. Signatures

- DB tables: `research_shortlist_runs`, `research_shortlist_candidates`;
  nullable `research_shortlist_runs.generation_task_run_id` references
  `task_runs.id` with `ON DELETE SET NULL`.
- Scoring model: `daily_research_score_v1`.
- Eligibility rule set: `instock_composite_selection_v1`.
- Service write:
  `generate_research_shortlist(ResearchShortlistGenerateInput, *, session)`.
- Service reads: `get_latest_research_shortlist(...)` and
  `get_research_shortlist(run_id, *, session)`.
- Point-in-time selector:
  `screen_local_stock_selection(..., as_of: date | None = None,
  unbounded_results: bool = False)`.
- APIs:
  - `POST /research-shortlists/generate`
  - `GET /research-shortlists/latest?market=CN&profile_id=<profile>`
  - `GET /research-shortlists/{run_id}`
- Common response:
  `{ status, run, items, research_signal_only, safety }`.

### 3. Contracts

- V1 supports locally stored active `CN` `stock` instruments only. Public
  FastAPI/browser callers cannot provide an arbitrary historical date or
  TaskRun lineage. The daily research orchestrator may pass an internal
  `verified_decision_date` established by the completed-market watermark and a
  nullable `generation_task_run_id`; manual calls still derive the latest
  in-scope stored daily-bar date.
- Publication keeps the existing readiness thresholds unchanged: 95% daily
  bars, 90% critical technical indicators, 80% complete fundamentals, with all
  three A-share exchanges represented.
- Every readiness and eligibility query is point-in-time. Daily bars use
  `trade_date <= decision_date`; indicators use timestamps before the next UTC
  day; fundamentals use `as_of <= decision_date`; news uses both
  `published_at` and `SentimentSignal.created_at` before the next UTC day.
  These filters must be applied before latest/max subqueries.
- Publication performs a second defensive point-in-time check. A candidate
  containing later bar, indicator, fundamental, news, or sentiment evidence is
  excluded with `POST_DECISION_EVIDENCE`; every published entry bar is exactly
  on the decision date.
- Profile rules remain all-or-nothing eligibility gates. All eligible candidates
  are scored before the final `1..20` limit. AI text and uncited prose have zero
  effect on membership, score, or rank.
- Score order is total score descending, minimum rule buffer descending, then
  symbol ascending. The saved record includes dimension/rule contributions,
  supporting/opposing factors, gaps, invalidation conditions, entry provenance,
  evidence, citations, and research-only safety metadata.
- Generation-key inputs are market, asset type, profile, normalized effective
  criteria, decision date, eligibility/scoring versions, and shortlist limit.
  Set-like criteria are canonicalized before hashing and persistence:
  candlestick pattern codes are trimmed, lowercased, deduplicated, and sorted;
  sentiment is trimmed and lowercased.
- Idempotency is established before explanation generation. PostgreSQL takes a
  transaction-scoped advisory lock derived from the generation key; non-
  PostgreSQL/test runtimes use a bounded process-local striped lock. The
  existing-run check, explanation, candidate assembly, and commit stay inside
  that serialized section. The unique generation-key constraint is the final
  database defense.
- A run and all candidates commit atomically. Read-only early returns and error
  paths roll back open transactions; process-local locks are always released.
- The first committed run stores its optional generation TaskRun lineage.
  Generation-key reuse returns that original nullable lineage and never
  rewrites it for a later manual, scheduled, or retry caller.
- `latest` with no row returns HTTP 200 and `status="no_data"`; missing detail
  returns 404; invalid profile/override returns 400; readiness failure returns
  409 with a structured code and no partial rows.
- Locale is cohort provenance, not generation identity. The first committed
  explanation is immutable. UI chrome, safety, factors, gaps, invalidations,
  readiness, and diagnostics are localized from structured fields/codes. If a
  saved explanation locale differs from the current page locale, the raw prose
  is not rendered; show a localized immutable-cohort notice while preserving
  the structured evidence view.
- Payloads and UI remain research-only and must not emit buy/sell/hold, target
  price, position sizing, portfolio weight, order, broker, or execution intent.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| No in-scope daily bar | 409 `NO_IN_SCOPE_DAILY_BARS`; no run |
| Coverage below 95/90/80 or exchange requirement | 409 `EVIDENCE_COVERAGE_NOT_READY`; no run |
| Future evidence appears in coverage storage | Ignore it before latest/max aggregation |
| Future evidence reaches a selected candidate | Exclude with `POST_DECISION_EVIDENCE` |
| Candidate entry bar is stale | Exclude with `STALE_ENTRY_BAR` |
| All eligible candidates are stale/contaminated | 409 `NO_DECISION_DATE_ALIGNED_CANDIDATES` |
| Entry bar disappears before commit | 409 `ENTRY_BAR_CHANGED_DURING_GENERATION` |
| Unknown profile/override/rule | 400 or service `ValueError`; no run |
| Invalid internal verified date or generation TaskRun UUID | Service `ValueError`; no run |
| Original generation TaskRun is deleted | Nullable shortlist lineage becomes null; cohort remains |
| Same semantic criteria use different order/case/duplicates | Same generation key and run ID; no second explanation |
| Concurrent same-key requests | One committed run; one explanation invocation |
| LLM unavailable, fails, or invents symbol/citation | Deterministic validated fallback; rank unchanged |
| Latest run absent | HTTP 200 `no_data`, `run=null`, `items=[]` |
| Detail run absent/invalid | HTTP 404 |
| Explanation locale differs from page locale | Hide raw prose; render localized provenance notice |

### 5. Good / Base / Bad Cases

- Good: ready local evidence produces one committed run with differently scored,
  uniquely ranked candidates and frozen decision-date provenance.
- Good: two sessions request pattern codes as `[' Hammer ', 'DOJI', 'hammer']`
  and `['doji', 'HAMMER']`; both receive the same run and the explanation
  provider is called once.
- Good: future technical/fundamental rows exist, but coverage and selector use
  only evidence available by the decision date.
- Base: no candidate passes the transparent profile; an auditable committed run
  may contain zero candidates and retains coverage/diagnostics.
- Base: an English cohort is opened from a Chinese page; structured content is
  Chinese and a Chinese notice explains why original explanation prose is not
  shown.
- Bad: readiness counts future evidence, the selector reads unrestricted latest
  rows, or a model changes shortlist membership/rank.
- Bad: locale or LLM availability creates a duplicate cohort, or backend English
  messages/disclaimers are displayed directly on the Chinese page.

### 6. Tests Required

- Scorer tests cover every normalization family, dimension renormalization,
  stable ordering, different totals, and unknown rules.
- Coverage/selector tests insert future bars, indicators, fundamentals, news,
  and sentiment, then assert decision-date results and unchanged 95/90/80
  thresholds.
- Service tests cover semantic generation-key normalization, two-session
  concurrency with one explanation call, duplicate-key fallback, stale/post-
  decision rejection, internal verified cutoff, immutable TaskRun lineage,
  public-request exclusion, atomic rollback, no provider calls, and
  deterministic AI fallback.
- Domain/migration tests cover both tables, generation/rank uniqueness, cascade,
  latest-index column order, and upgrade/downgrade.
- API/proxy tests cover generate/latest/detail, 400/409/404/no-data behavior,
  body/status/content-type forwarding, and `no-store` reads.
- UI/page tests cover loaded/empty/error/generating states, first-screen order,
  deep links, symbol handoff, both locales, injected opposite-language prose,
  unknown structured codes, and localized safety text.
- Final gate: focused pytest, full pytest, touched-file Ruff, full Vitest,
  TypeScript, both locale JSON files, Alembic head, Trellis validation, and
  `git diff --check`.

### 7. Wrong vs Correct

#### Wrong

```python
latest = session.query(TechnicalIndicator).order_by(
    TechnicalIndicator.as_of.desc()
).first()
explanation = call_llm(shortlist)
existing = find_run(generation_key)
```

This can use future evidence and invoke the model twice before idempotency is
established.

#### Correct

```python
with serialized_generation(session, generation_key):
    existing = find_run(generation_key)
    if existing is not None:
        return serialize(existing)
    shortlist = screen_local_stock_selection(session=session, as_of=decision_date, ...)
    explanation = explain_fixed_shortlist(shortlist)
    commit_run_and_candidates_once()
```

The readiness gate and selector use the same decision-date boundary, and the
generation key serializes the entire explanation/persistence window.
