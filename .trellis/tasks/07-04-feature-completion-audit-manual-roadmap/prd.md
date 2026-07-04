# Feature Completion Audit Manual and Roadmap

## Goal

Audit whether the requested Phase 2 and Phase 3 financial-platform features are fully implemented, complete any missing lightweight deliverables, update user/developer manuals when the implemented feature set is complete enough, and compare the platform against professional financial websites to produce an executable improvement roadmap.

## Background

The user previously requested automatic implementation, testing, commits, pushes, Trellis usage, and multi-agent assistance for Phase 2 and Phase 3 financial features. Recent commits indicate completed slices for technical indicators, intraday charts, and market-depth fallback contracts, but the repository must be inspected rather than assuming all features are complete.

Current known repository state before this task starts:

- A new Trellis task exists at `.trellis/tasks/07-04-feature-completion-audit-manual-roadmap`.
- The working tree has a known unrelated line-ending/noise modification in `apps/web/app/api/recommendations/route.ts`; this task must not include it unless audit evidence shows it is directly required.
- There are still several active Trellis tasks whose status may not reflect the latest commits, so completion should be determined from code/tests/docs evidence first and Trellis metadata second.

## Requirements

- Produce an evidence-based completion matrix for the requested Phase 2 features:
  - K-line chart interaction enhancements, including zoom and moving averages.
  - Intelligent recommendation module, including breakout and oversold signals.
  - Hot-sector rotation, including fund-flow-oriented presentation.
  - Comparison analysis tooling, including correlation analysis.
- Produce an evidence-based completion matrix for the requested Phase 3 features:
  - Intraday chart.
  - Market-depth data, including five-level order book and large-order handling.
  - Technical indicator library, including MACD, RSI, and KDJ.
  - AI assistant.
- If a feature is missing or incomplete, create a detailed implementation plan and continue implementation when the work is within this task's scope.
- If all requested features are complete enough for the current MVP, update the relevant manuals/documentation so users and maintainers can discover and operate the implemented capabilities.
- Compare the current platform with professional financial websites and trading terminals, focusing on capability coverage, market-data integrity, UX, analytics depth, explainability, and operational readiness.
- Convert comparison gaps into a prioritized Trellis-backed improvement roadmap with actionable tasks.
- Preserve the degraded-safe data principle: unsupported provider data must be labeled unavailable/degraded rather than fabricated.
- Run focused validation for any changed files and do not commit unrelated noise files.

## Acceptance Criteria

- [ ] Completion matrix includes every Phase 2 and Phase 3 feature named by the user, with evidence links to code/tests/docs where possible.
- [ ] Missing or incomplete features have concrete plans, owners/files, validation commands, and acceptance criteria.
- [ ] Manuals/documentation are updated when feature completion is sufficient, or gaps blocking manual completion are explicitly listed.
- [ ] Professional-site comparison identifies current strengths, missing capabilities, and prioritized optimizations.
- [ ] A Trellis-backed roadmap is created for follow-up improvements that are too large for this task.
- [ ] Any implementation or documentation edits pass focused checks.
- [ ] Git commits and pushes include only task-related files; `apps/web/app/api/recommendations/route.ts` remains excluded unless intentionally changed for this task.

## Open Questions

- Whether the user wants professional comparison to target a specific market style, such as CN retail terminals, US broker research portals, or general global finance websites. If not specified, use a balanced benchmark set.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
