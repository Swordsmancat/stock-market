# Professional Chart Workspace Enhancements

## Goal

Add TradingView-style chart workspace follow-ups: saved layouts, drawing tools, linked intervals, presets, and chart-linked alerts.

## Requirements

- Build on the existing `AdvancedCandlestickChart`, chart indicator helpers, and instrument detail page.
- Add a professional chart-workspace plan before implementation, including saved layouts, drawing/annotation tools, indicator presets, multi-pane layout, and multi-timeframe synchronization.
- Include chart-linked alert requirements only as research/alert workflow integration; do not add brokerage execution behavior.
- Preserve current MA, BOLL, volume, MACD, RSI, KDJ, range controls, dark-mode behavior, and degraded/empty states.
- Keep user-visible labels localized in English and Chinese.
- Define storage boundaries for saved layouts and presets before writing code.

## Acceptance Criteria

- [ ] `design.md` defines chart workspace state, persistence, drawing model, and alert integration boundaries.
- [ ] `implement.md` breaks work into independently testable slices.
- [ ] Users can save and restore at least one chart layout/preset without losing current indicator controls.
- [ ] Drawing or annotation affordances are available without breaking responsive layout.
- [ ] Multi-timeframe or multi-pane behavior is covered by focused component tests.
- [ ] Documentation explains that chart alerts are research notifications, not trading instructions.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
