# Technical Indicators Workbench

## Goal

Complete MACD RSI KDJ BOLL indicator library integration and configurable chart display.

## Requirements

- Complete the technical indicator library around the existing analytics, service, API, and chart foundations.
- Support MACD, RSI, KDJ, BOLL, and moving averages in a user-facing indicator workbench.
- Preserve current daily-bar indicator persistence while adding missing MACD/KDJ calculations where needed.
- Expose configurable display controls for multiple indicators without overloading the main price chart.
- Localize all user-facing labels in English and Chinese.

## Acceptance Criteria

- [ ] MACD and KDJ calculations have focused automated tests.
- [ ] Stored/API indicator payloads include the newly supported indicators or explicitly document why they are computed client-side only.
- [ ] Instrument detail UI can add/remove supported indicators.
- [ ] Indicator parameters are configurable for at least common defaults without breaking existing MA/RSI/BOLL behavior.
- [ ] Relevant pytest and web tests pass.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
