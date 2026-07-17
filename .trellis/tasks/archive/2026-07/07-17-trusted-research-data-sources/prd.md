# Expand trusted research data sources

## Goal

Absorb the useful public-source ideas from the reviewed external system while
keeping this repository's personal-research, database-first, auditable design.

## Requirements

- Deliver sources in this order: NBS qualification/fallback, China money-market
  repo rates, economic calendar, index valuation, then continuous public news.
- Reuse PostgreSQL observations and existing explicit refresh boundaries; do
  not add MongoDB, frontend-triggered crawlers, private mirrors, or committed
  cookies/credentials.
- Every stored value must retain provider, upstream field/series identifier,
  source URL, retrieval time, and methodology.
- GET dashboard/detail routes remain database-only and must preserve the last
  successful observation when a provider fails.
- A candidate whose identifiers or semantics cannot be independently verified
  is documented as blocked rather than promoted to production.

## Acceptance Criteria

- [ ] NBS candidate interfaces and mappings are qualified without guessing
  omitted identifiers.
- [ ] FR007/FDR007 observations are stored with truthful semantics.
- [ ] Economic-calendar observations are stored and queryable.
- [ ] Index valuation observations are stored with explicit PE/dividend fields.
- [ ] Continuous public news is deduplicated, stored, and bounded.
- [ ] Source replacement documentation identifies the adapter, persistence
  path, upstream authority, and safe fallback for every new source.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
