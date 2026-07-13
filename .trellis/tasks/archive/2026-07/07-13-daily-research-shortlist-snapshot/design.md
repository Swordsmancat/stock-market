# Persisted daily research shortlist - design

## Service boundaries

- Keep `screen_local_stock_selection` as the eligibility/evidence loader. Add an
  internal unbounded-result option so publication can score every match before
  applying its final limit; public API limits stay unchanged.
- Add `packages/services/research_shortlists.py` for readiness, scoring,
  generation-key construction, transactional persistence, serialization,
  latest/detail reads, and deterministic diagnostics.
- Extract/reuse an explanation helper in `stock_discovery.py` so both current
  discovery and publication keep the same fail-closed LLM symbol/citation
  validation without running the selector twice.
- Add a dedicated `apps/api/routers/research_shortlists.py` router. It remains a
  thin validation/HTTP mapping layer.

## Scoring model

Identifier: `daily_research_score_v1`.

Existing active rules remain eligibility gates. For each matched rule, compute a
buffer score in `[0.5, 1]`: `0.5` means exactly at the invalidation threshold;
`1` means the configured favorable buffer is fully reached. Exact categorical
matches score `0.75` because the evidence proves membership but no magnitude.

### Rule normalization

- `max_pe_ratio`: favorable distance below the threshold divided by
  `max(threshold, 1)`.
- `min_revenue_growth`, `min_net_margin`: favorable distance above threshold
  divided by `0.20` (20 percentage points).
- RSI/MFI min rules: distance to threshold divided by `100 - threshold`;
  max rules: distance below threshold divided by `threshold`.
- William %R uses domain `[-100, 0]`: min rules divide by `0 - threshold`; max
  rules divide by `threshold - (-100)`.
- Chip ratio and sentiment confidence use domain `[0, 1]` with the equivalent
  distance to the favorable boundary.
- Latest volume, traded amount, and article count use
  `log10(max(actual / threshold, 1))`, capped at one; ten times the threshold is
  the full buffer.
- Price above MA uses `(close / ma - 1) / 0.10`, capped at one; 10% above MA is
  the full buffer.
- Required patterns and required sentiment are categorical exact matches and
  score `0.75`.

For numeric rules, `buffer = 0.5 + 0.5 * clamp(favorable_distance, 0, 1)`.
Unknown rule codes fail generation rather than receiving an invented score.

### Dimensions and weights

Rules are grouped as:

- fundamental: PE, revenue growth, net margin (base weight `0.40`);
- technical: RSI, price/MA, patterns, MFI, William %R, chip ratio (`0.35`);
- liquidity: volume and traded amount (`0.20`);
- news: article count, sentiment, confidence (`0.05`).

Only active dimensions participate; base weights are renormalized to sum to one.
A dimension score is the arithmetic mean of its active rule buffers. Total score
is the weighted dimension sum, rounded to four decimals. The minimum rule buffer
is a secondary quality/tie-break signal. Final order is total descending,
minimum buffer descending, symbol ascending.

The payload records rule code, field, actual, threshold, normalization ID,
buffer, dimension, normalized dimension weight, and weighted contribution.
Supporting factors are the three highest rule buffers at or above `0.75`.
Opposing factors are the two lowest buffers below `0.75`; the list may be empty,
while invalidation conditions are always present for every active gate.

## Freshness and readiness

1. Query the latest in-scope `DailyBar.trade_date` as decision date.
2. Call existing `get_evidence_coverage(..., as_of=decision_date)` and require
   its full readiness status. Persist the returned coverage snapshot.
3. Run eligibility over all matching candidates.
4. Exclude and diagnose any candidate whose serialized latest bar date differs
   from the decision date.
5. Record technical/fundamental as-of values and candidate-level freshness gaps
   when available. Required missing values already fail eligibility.

The service never reaches a provider. It reads the same local SQLAlchemy session
and commits only after the complete snapshot is assembled.

## Persistence

### ResearchShortlistRun

- UUID primary key; unique indexed `generation_key`.
- `decision_date`, `generated_at`, `market`, `asset_type`, `profile_id`,
  `rule_set`, `scoring_model`, `locale`, `shortlist_limit`.
- JSON snapshots: default/effective criteria, overrides, dimension weights,
  candidate scope, coverage, diagnostics, explanation model, citations, safety.
- `explanation_markdown` text and `research_signal_only` boolean.

### ResearchShortlistCandidate

- UUID primary key and run foreign key with delete cascade semantics at the DB
  constraint level.
- Instrument foreign key plus symbol/name/market snapshots.
- Unique `(run_id, instrument_id)` and `(run_id, rank)` constraints.
- Rank, numeric total/minimum-buffer scores, entry date/close, and entry
  provenance scalar fields.
- JSON snapshots: factor scores, supporting/opposing factors, data gaps,
  invalidation conditions, evidence, matched rules, and citations.

Use JSON with the repository's PostgreSQL JSONB variant pattern. The service
flushes the run, adds all candidates, then commits once. On `IntegrityError`
from a concurrent generation-key insert, roll back and return the winner.

## Generation key and immutability

Build compact sorted canonical JSON from market, asset type, profile ID,
effective criteria, decision date, eligibility/scoring versions, and shortlist
limit, then hash with SHA-256. Locale and LLM availability do not create a
second cohort. The first committed explanation is immutable; repeated requests
return it without model invocation.

## API responses

`POST /research-shortlists/generate` returns `200` with the committed resource.
Invalid profile/override returns `400`. No bars or coverage not ready returns
`409` with a sanitized reason and no run. Unexpected persistence errors remain
server errors and roll back.

`GET /research-shortlists/latest` returns a common payload with
`status="no_data"`, `run=null`, and an empty item list when none exists.
`GET /research-shortlists/{uuid}` returns the resource or `404`.

## Frontend

- Centralize TypeScript contracts in
  `apps/web/lib/daily-research-shortlist.ts`.
- Add `DailyResearchShortlistPanel` using existing financial-terminal and table
  primitives, Lucide icons, stable table columns, and localized strings.
- Add browser proxies for latest and generation using no-store semantics and
  transparent upstream status/body handling.
- Server-load latest in `ai-research/page.tsx`, render the new panel first, the
  existing `AiResearchDesk` second, then coverage/manual-discovery tools.
- Use a normal localized link for deep analysis; query lineage is additive and
  ignored safely by the current instrument page.

## Compatibility and rollback

- Existing discovery endpoints and UI remain functional and tested.
- Alembic `0020` is additive. Downgrade drops only candidate/run tables in
  dependency order.
- Removing the panel/proxies/router and downgrading `0020` restores the prior
  product without modifying old records or services.
