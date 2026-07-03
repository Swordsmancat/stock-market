# AI Market Assistant

## Goal

Add a natural-language market assistant built on existing report generation and traceable market context.

## Requirements

- Add a natural-language market assistant that builds on existing report-generation and market-data context.
- Responses must cite or summarize the data sources used, and must avoid unsupported claims.
- Provide safe boundaries around investment advice, including clear educational/disclaimer language.
- Support questions about symbols, reports, indicators, recommendations, and dashboard context.
- Keep assistant UI labels localized in English and Chinese.

## Acceptance Criteria

- [ ] Assistant API accepts a user question and returns an answer with traceable context metadata.
- [ ] Assistant UI provides a conversational entry point and handles loading/error states.
- [ ] Responses include safe output boundaries and do not fabricate unavailable data.
- [ ] Tests cover successful contextual answers and unavailable-context fallback.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
