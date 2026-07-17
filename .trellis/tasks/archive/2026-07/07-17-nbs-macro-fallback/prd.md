# Qualify a direct NBS macro fallback

## Goal

Determine whether the National Bureau of Statistics public interfaces described
by the reviewed external system can safely become a direct production fallback
for existing China macro observations.

## Requirements

- Verify endpoint reachability separately from indicator identity and unit
  semantics.
- Never copy abbreviated `cid`, `rootId`, or omitted `indicatorIds` into code.
- Do not add a production adapter until the complete immutable identifiers and
  response fields can be verified against an official NBS response.
- Record the intended database-first fallback contract and the exact evidence
  required to unblock implementation.
- Preserve the existing AkShare source and all stored observations.

## Acceptance Criteria

- [x] Both legacy `easyquery` and current `esData` candidates are probed without
  credentials or writes.
- [x] Qualification result and blockers are added to the macro source registry.
- [x] No guessed mapping, cookie, private endpoint, or runtime regression is
  introduced.
- [x] The next viable source phase is identified and can proceed independently.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
