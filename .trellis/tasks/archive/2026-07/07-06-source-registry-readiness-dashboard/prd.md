# Information Source Registry and Readiness Dashboard

## Goal

Expose a source-aware registry/readiness layer for macro indicators, hard-to-find research sources, reports, news, and user-curated seed files so the personal dashboard shows what sources exist, what is missing, and what AI can summarize safely.

## Requirements

### R1. Source Registry

- Define a curated registry of information sources that support the revised product direction:
  - official macro sources such as FRED for US rates/inflation/liquidity.
  - China macro sources such as PBOC/manual-reviewed CN M2.
  - valuation/manual seed sources for Buffett Indicator components.
  - SEC/announcement/transcript-style document sources as future hard-to-find inputs.
  - existing platform stores: generated reports, stored news, watchlists, macro observations.
- Each source entry must describe:
  - stable `id`.
  - user-visible label.
  - category such as `macro`, `valuation`, `documents`, `news`, `reports`, `manual_seed`.
  - provider/source authority.
  - coverage/series IDs where known.
  - freshness policy.
  - current status: `configured`, `needs_adapter`, `needs_manual_seed`, `no_data`, or `future`.
  - why it matters for AI summaries.
  - next collection action.

### R2. Readiness Payload

- Expose source readiness inside the existing dashboard market overview payload.
- Do not add live network calls in this slice.
- Readiness should be derived from existing database state and static source definitions:
  - macro observations from `MarketIndicatorObservation`.
  - generated reports from `GeneratedReport`.
  - stored news from `NewsArticle`.
  - source definitions for official/future inputs.
- Missing sources must render as action-oriented gaps, not errors.

### R3. Frontend Dashboard

- Add a compact "Information source readiness" panel to the personal dashboard.
- Show source groups, current status, authority/provider, freshness policy, and next action.
- Keep the UI focused on personal information aggregation and AI summary readiness.
- Do not present this as a professional trading data entitlement matrix.

### R4. AI Summary Alignment

- The registry should make clear which sources can safely support AI summaries now and which are future/blocked.
- Entries should mention whether the source can be cited today or needs adapter/manual review first.
- No entry should imply investment advice, real-time macro coverage, or licensed document access unless actually implemented.

### R5. Documentation

- Update README/manual to mention the source readiness layer.
- The manual should explain that the platform intentionally surfaces data gaps so the user knows what AI can and cannot summarize.

## Acceptance Criteria

- [x] A backend source registry/readiness helper exists and is covered by focused service tests.
- [x] `/dashboard/market-overview` includes additive `information_sources` data without breaking existing payload fields.
- [x] The homepage renders a source readiness panel with status and next-action text.
- [x] Frontend tests cover the panel and at least one hard-to-find source action.
- [x] README/manual describe the feature without claiming live macro feeds or professional terminal parity.
- [x] Validation passes or known unrelated failures are documented in `implement.md`.

## Completion Notes

- P1 readiness MVP completed on 2026-07-06.
- Source strategy research is recorded in `research/source-strategy.md`.
- This slice intentionally adds no live FRED/PBOC/SEC/transcript network ingestion. Those remain follow-up adapter/manual-seed tasks.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
