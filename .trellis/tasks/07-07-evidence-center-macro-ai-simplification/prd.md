# Simplify Evidence Center for macro AI workflow

## Goal

Make the Evidence Center match the user's actual workflow: view online/API-backed macro indicators, read AI summaries, save reusable research briefs, and then choose stocks for AI analysis or recommendations. Manual local seed import, Source Notebook uploads, and deterministic follow-up queues should remain available for edge cases, but they should not dominate the default page.

Also fix a visible localization bug where `ResearchSourceNotebook.completenessSummary` appears on the page instead of a translated completeness count.

## Confirmed Facts

- `/zh/evidence` currently loads, but the first screen shows manual seed import and Source Notebook before AI evidence summary, saved research briefs, and macro/valuation evidence.
- The page visibly renders `ResearchSourceNotebook.completenessSummary` because placeholder-based translation strings are being read as formatted messages instead of raw templates.
- The user does not expect to upload local notes or local seed data as a normal workflow.
- The user's desired workflow is online/API data first: macro indicators, selected-stock AI analysis, and AI recommendations.
- Current backend capabilities for manual seed import, Source Notebook, source ingestion, follow-up queue, and saved briefs should not be deleted in this task.

## Requirements

1. Fix visible translation-key rendering for Source Notebook completeness summaries.
2. Fix the same placeholder-template pattern for saved research brief labels if present.
3. Reorder the Evidence Center so the default flow prioritizes:
   - page overview metrics,
   - AI evidence summary,
   - saved research brief inbox,
   - macro/valuation evidence table,
   - information source readiness.
4. Move manual seed import, Source Notebook/source ingestion, and research follow-up queue below the primary analysis sections inside a clearly optional advanced/source-review area.
5. Adjust user-facing Evidence Center copy away from "local upload first" positioning and toward "online/API-backed macro evidence and AI synthesis first."
6. Keep existing advanced/manual workflows functional for future cases where API data is missing or a difficult source needs manual review.

## Acceptance Criteria

- [ ] `/zh/evidence` no longer displays raw translation keys such as `ResearchSourceNotebook.completenessSummary`.
- [ ] Evidence Center's top-level visual order presents AI/macro research before manual seed import or Source Notebook controls.
- [ ] The seed import, Source Notebook, and follow-up queue remain reachable without removing their existing components.
- [ ] Frontend tests cover the corrected translation-template behavior and new section order.
- [ ] TypeScript and focused Evidence Center tests pass.

## Notes

- Product decision: these manual evidence tools are not useless, but they are fallback/admin workflows. They are useful only when online/API sources are missing, licensed data cannot be fetched automatically, or the user wants to manually preserve a rare source. They should not be the default path.
