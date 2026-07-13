# Outcome contract audit

## Evidence reviewed

- Parent decision-loop PRD/design and the completed daily-shortlist contract.
- `ResearchShortlistRun`, `ResearchShortlistCandidate`, `DailyBar`, `Instrument`,
  and migration `0020`.
- Existing recommendation evaluators, market-index provider mappings, daily-bar
  replacement logic, shortlist APIs, AI Research page, Next proxies, locale
  handling, and focused tests.
- Independent domain, UI/API, and risk reviews performed on 2026-07-13.

## Conclusions

- The useful next product step is outcome feedback, not more provider breadth:
  it tests whether the research shortlist is informative.
- Horizon N is the candidate's own Nth stored bar after entry. Natural-day or
  benchmark-array indexing is invalid.
- Candidate absolute results and CSI 300 comparison need independent states.
  Exact benchmark data may be missing without invalidating the candidate result.
- Terminal-only candidate persistence plus derived pending state best preserves
  immutability. A pending benchmark may be enriched once against frozen dates.
- A date cutoff alone cannot prove a daily row is final. Eligibility also
  requires ingestion at/after 16:00 Shanghai time on the trade date or on a
  later local date, so an abandoned intraday row never matures a horizon.
- Outcome `as_of` limits market observation dates, not database system time.
  Later finalized backfills on or before that date remain eligible; V1 does not
  claim bitemporal reconstruction of what the database knew at an earlier time.
- The benchmark must be a dedicated `CN/index/cn_csi_300` instrument. The CN
  stock `000300` and AkShare stock-history endpoint are unsafe substitutes.
- Existing qfq storage has no factor-vintage identity. V1 therefore verifies
  the current entry against the frozen entry and labels accepted qfq results as
  a proxy; a mismatch blocks the horizon.
- `tushare.pro.daily` currently returns unadjusted `pro.daily` prices while the
  ingestion coordinator labels them qfq. Future writes must use raw and outcome
  evaluation must source-normalize existing mislabeled rows before comparing
  adjustment bases.
- A separate tracking endpoint and panel prevent outcome failures from breaking
  the already-published shortlist workflow.

## Test risks to preserve

- 4/5, 19/20, 59/60 boundaries and completed-day cutoff.
- Suspensions, N+1 exclusion, invalid OHLC, entry revision, adjustment mismatch,
  and mixed source with compatible adjustment.
- Pending-ready `N/N` reads before evaluation, plus legacy Tushare raw/qfq
  provenance normalization and raw/qfq mixed-path blocking.
- Exact benchmark dates, stock/index identity isolation, and null comparison.
- Inactive cohort retention, idempotency/concurrency, immutable terminal values,
  aggregate identities, and constant query count.
- Overlapping horizon insert races must use conflict-ignore/savepoint semantics
  so one winner does not roll back unrelated terminal rows.
