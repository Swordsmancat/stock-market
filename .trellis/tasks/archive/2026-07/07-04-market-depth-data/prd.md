# Market Depth Data

## Goal

Add level-2 style depth, recent trades, large order tracking, and fund-flow fallback contracts.

## Requirements

- Define and expose level-2 style market depth contracts without assuming every provider supports them.
- Support five-level bid/ask display, recent trades, large-order identification, and fund-flow summary when data exists.
- Surface unavailable/degraded provider states clearly in both API payloads and UI.
- Do not present mock depth data as real market data.

## Acceptance Criteria

- [ ] Provider capability matrix documents depth/trades/fund-flow support and fallback behavior.
- [ ] API contracts for order book, recent trades, large orders, and fund flow are typed and tested.
- [ ] Instrument detail UI renders data when present and clear unavailable states when not.
- [ ] Large-order threshold is explicit and covered by tests.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
