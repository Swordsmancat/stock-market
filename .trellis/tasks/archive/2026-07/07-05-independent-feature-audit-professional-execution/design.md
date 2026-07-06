# Independent Feature Audit and Professional Benchmark Execution - Design

## Role of this parent task

This task is an integration and orchestration task. It should not duplicate the implementation details already owned by narrower tasks. Its responsibilities are:

- collect evidence from active/archived Trellis tasks, docs, tests, and browser smoke checks;
- classify current implementation status honestly;
- map professional-product gaps to focused follow-up tasks;
- decide when existing tasks can be archived or must remain active for evidence/future parity work.

## Task map

### Existing tasks to reuse

- `07-03-frontend-ui-polish`
  - Owns settings-driven market-color behavior, UI polish, manual/browser smoke validation, and screenshot/WCAG evidence.
  - Should be treated as implementation/evidence complete for the sampled MVP routes after `07-05-dashboard-visual-evidence-wcag`.

- `07-03-professional-financial-dashboard`
  - Owns the deeper Yahoo Finance / TradingView / professional-dashboard direction.
  - Should remain active as a strategic task or be split into focused child tasks for screener, workspace persistence, backtesting UI, and provider trust.

### Recommended future child tasks

1. `dashboard-visual-evidence-wcag`
   - Completed: captured durable screenshots and explicit light/dark contrast proof.
   - Closed the remaining evidence-only UI gap.

2. `provider-trust-and-data-sla-dashboard`
   - Expose provider freshness, source, degraded/no-data/mock status, and incident/SLA status across professional surfaces.
   - Prevents overclaiming real-time or Level-2 support.

3. `professional-screener-watchlist-workflows`
   - Saved filters, custom columns, richer alerts, signal browsing.

4. `professional-workspace-persistence`
   - Dashboard/chart layouts, symbol sets, panel preferences, and workspace presets.

5. `backtesting-and-signal-history-ui`
   - Persisted signal history, research-only backtest UI, costs/slippage assumptions, walk-forward diagnostics.

## Status classification model

Use the following labels in final reporting and task documents:

- `complete_for_mvp` — implemented, tested, documented, and usable for the current research workflow.
- `provider_boundary_complete` — contract/UI exists, but real provider validation or entitlement remains future work.
- `evidence_only_remaining` - historical/classification state for implementation that lacks screenshot/WCAG/manual proof; no sampled MVP UI route currently remains in this state after `07-05-dashboard-visual-evidence-wcag`.
- `professional_gap` — not implemented and should become a focused follow-up task only if prioritized.

Current sampled MVP UI routes have no evidence-only blocker after `07-05-dashboard-visual-evidence-wcag`; remaining gaps are professional roadmap gaps.

## Professional benchmark dimensions

Compare the app across these dimensions:

1. Market overview density and responsiveness.
2. Quote freshness, source transparency, and degraded/no-data behavior.
3. Charting depth, indicator coverage, annotations, and workspace persistence.
4. Watchlist/screener/alert workflow breadth.
5. Sector, breadth, fund-flow, and rotation analytics.
6. AI/research corpus quality, citations, and diagnostics.
7. Portfolio analytics, attribution, risk, and scenario support.
8. Operational trust: data SLA, provider incidents, entitlements, and auditability.

## Compatibility and safety

- Keep all professional claims tied to validated implementation evidence.
- Preserve no-fabrication behavior for market data, intraday, depth, sectors, and AI citations.
- Do not convert semantic colors such as success/error/destructive/bid/ask into market movement colors.
- Do not revert unrelated existing work in the dirty working tree.

## Rollback considerations

- Parent task changes are documentation/task metadata only unless a child implementation task is explicitly started.
- If task linking creates an incorrect relationship, remove it with `task.py remove-subtask` rather than editing unrelated task state manually.
