# Intraday Chart

## Goal

Add intraday minute chart with previous close, average price, volume, hover details, and graceful fallback.

## Requirements

- Add an intraday chart experience for instrument detail pages.
- Define a minute-data payload contract that can work with real provider data or an explicit unavailable/degraded fallback.
- Show intraday price, previous close reference, average price line, and intraday volume where data is available.
- Provide hover details for intraday points.
- Avoid silently fabricating live intraday data when provider support is unavailable.

## Acceptance Criteria

- [ ] A documented intraday payload shape is available to frontend and backend code.
- [ ] Instrument detail page can show an intraday chart or a clear unavailable/degraded state.
- [ ] Previous close, average price, and volume are displayed when supported by the payload.
- [ ] Focused tests cover available and unavailable intraday states.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
