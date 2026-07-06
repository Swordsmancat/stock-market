# Source-to-Seed Template Assistant

## Goal

Turn source readiness collection guidance into actionable audited seed templates for macro and valuation observations without live fetching, scraping, or treating links as AI evidence.

## Requirements

### R1. Source-to-Seed Templates

- Extend applicable information-source readiness items with audited seed-template guidance.
- The template guidance should cover the sources where local macro/valuation observations can be imported today:
  - FRED US rates: `us_10y_yield`, `us_2y_yield`, `us_10y_2y_spread`.
  - FRED US inflation: `us_cpi_yoy`.
  - FRED US liquidity: `us_m2_yoy`.
  - PBOC / China M2 manual source: `cn_m2_yoy`.
  - Buffett Indicator manual valuation components: `buffett_indicator_cn`, `buffett_indicator_hk`, `buffett_indicator_us`.
  - User seed files: generic audited macro indicator observations.
- Guidance must include:
  - target indicator codes.
  - required seed fields.
  - a JSON template.
  - a CSV header and example row.
  - review checklist items.
  - the existing import command.

### R2. Evidence and Citation Boundaries

- Seed templates are operator guidance only. They must not become `dashboard_brief.citations`, assistant citations, or configured evidence.
- Placeholder values must be visibly placeholders, not realistic market observations.
- The feature must not call FRED, PBOC, World Bank, SEC, or any external website.
- The feature must not scrape, store external documents, or introduce new database tables.
- Existing source readiness statuses must keep their current meaning.

### R3. Dashboard Visibility

- Homepage source readiness items should show seed-template guidance where available.
- The UI should be framed as a personal research data-entry helper, not a trading-terminal data entitlement feature.
- Keep the source links visually separate from seed templates and citable evidence.
- Use translated labels in English and Chinese.

### R4. Documentation and Specs

- README/manual should explain that source-to-seed templates help prepare reviewed local seed files.
- Docs must repeat the no-scraping, no-automatic-ingestion, no-advice, and not-citeable-until-imported boundaries.
- Backend citation/source-readiness spec should capture the seed-template contract.

## Acceptance Criteria

- [ ] `get_information_source_readiness_payload()` returns seed-template metadata for FRED rates, Buffett manual valuation components, and user seed files.
- [ ] The template payload remains additive and does not affect source status or evidence counts.
- [ ] Backend tests assert target codes, required fields, JSON placeholder template, CSV row, and review checklist.
- [ ] `/dashboard/market-overview` still returns the source readiness payload with the template fields.
- [ ] Homepage renders seed-template guidance and import command for at least one macro source.
- [ ] Frontend tests cover visible template labels and placeholder values.
- [ ] README/manual/spec document the boundary that templates are guidance only and become citeable only after audited import.
- [ ] Focused backend/frontend checks pass; full checks pass or unrelated failures are documented.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
