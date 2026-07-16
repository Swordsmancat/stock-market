# Simplify AI research evidence context

## Goal

Make the AI Research Desk a readable personal research surface: foreground the
active symbol, deterministic signal, and stored evidence while keeping source
operations and raw diagnostics available but out of the default workflow.

## Background

- The Chinese runtime currently renders known macro names, internal indicator
  codes, backend English no-data reasons, source statuses, and maintenance
  instructions together in the main research column.
- The default assistant question includes uncitable macro gaps and raw provider
  refresh instructions such as FRED configuration steps.
- The project contract already distinguishes stored local observations from
  source readiness and requires maintenance-heavy controls to stay secondary.

## Requirements

- Use localized labels for the known macro indicator codes already supported by
  the dashboard; unknown indicators must fall back to their stored name, then
  code.
- Build the visible active macro summary and assistant question from citable
  local observations only. Do not describe missing observations as if they were
  evidence.
- Remove official-source readiness and provider maintenance instructions from
  the default assistant question. The question must still request risks,
  evidence gaps, and follow-up research questions.
- Keep source readiness and raw diagnostic details accessible inside one native
  `<details>` disclosure that is closed by default.
- In the default macro cards, hide known raw indicator codes and replace raw
  backend no-data prose with localized unavailable/gap copy. Preserve an
  unknown indicator's stored label and truthful unavailable state.
- Keep all backend payloads, citations, refresh actions, recommendation rules,
  shortlist generation, and trading boundaries unchanged.

## Acceptance Criteria

- [x] Chinese and English pages render localized labels for every known macro
      indicator used by the AI Research Desk.
- [x] The active macro summary and default assistant question contain only
      citable stored observations and localized fallback copy.
- [x] The default assistant question contains no provider setup action,
      missing-code list, or raw backend no-data reason.
- [x] Source readiness and source gaps remain available in a closed maintenance
      disclosure and are absent from the default visible flow.
- [x] Known raw macro codes and raw English no-data prose are absent from the
      default Chinese macro cards; unknown labels remain truthful.
- [x] Focused component tests, full Web tests, TypeScript, and browser checks
      pass without triggering an assistant request.

## Out Of Scope

- Adding macro providers, credentials, login/Cookies, refreshes, backfills, or
  model calls.
- Changing the daily shortlist table, score model, ranking, or outcome ledger.
- Hiding genuine unavailable states or fabricating macro values.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
