# Hard-to-Find Source Collection Links

## Goal

Turn the source readiness registry into actionable collection guidance by exposing official/legal source links, collection notes, and AI citation boundaries for hard-to-find macro/document sources.

## Requirements

### R1. Actionable Source Collection Guidance

- Extend the existing information-source readiness registry with collection guidance for hard-to-find inputs.
- Each relevant source should expose:
  - one or more official/legal collection links.
  - what the user should collect from that source.
  - whether the source can be cited today or needs adapter/manual review first.
  - a short legal/terms boundary note where needed.
- Keep this as metadata and guidance only. Do not fetch, scrape, or store external content in this slice.

### R2. Dashboard Payload Compatibility

- Add fields to `information_sources.items` and grouped items without breaking existing fields.
- Source readiness states must keep their existing meaning: `configured`, `needs_adapter`, `needs_manual_seed`, `no_data`, `future`.
- Links and collection notes must not become evidence citations unless there is local configured evidence such as a macro observation, generated report, or stored news item.

### R3. Frontend Visibility

- Render official/legal collection links and collection notes in the homepage source readiness panel.
- Keep the UI framed as personal research collection guidance, not a provider entitlement matrix or trading terminal feature.
- Links should open in a new tab and be safe for external navigation.

### R4. Documentation and Boundaries

- Update README/manual to explain that the platform now shows where to collect hard-to-find data.
- Explicitly say that this is not automated scraping, not licensed document ingestion, and not investment advice.

## Out of Scope

- Live FRED/PBOC/SEC adapters.
- Scraping, document ingestion, transcript storage, vector search, or source licensing workflows.
- Persisted user uploads or notes.
- New database tables.
- Broker/trading-terminal features.

## Acceptance Criteria

- [ ] Backend source definitions expose collection links and collection guidance in `get_information_source_readiness_payload()`.
- [ ] Service tests cover at least one official macro source, one manual valuation source, and one future document source.
- [ ] `/dashboard/market-overview` remains additive and continues returning the readiness panel data.
- [ ] Homepage renders collection links/notes for source readiness items.
- [ ] Frontend tests cover visible collection guidance and an external link.
- [ ] README/manual describe the feature and legal/no-scraping/no-advice boundaries.
- [ ] Focused backend/frontend checks and full tests pass or any unrelated failure is documented.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
