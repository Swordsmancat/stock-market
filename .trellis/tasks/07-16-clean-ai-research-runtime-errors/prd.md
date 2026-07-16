# Clean AI research runtime errors

## Goal

Make the existing AI Research page hydrate and render without React or
localization runtime errors during normal read-only use.

## Requirements

- Keep the current AI Research content, ordering, actions, research thresholds,
  payloads, and backend behavior unchanged.
- Place `provider` and `asOf` labels in the `AshareEvidenceCoverage` namespace
  and add the missing `ResearchShortlistOutcomes.asOf` label in English and Chinese.
- Ensure the daily shortlist and outcome panel have unique sibling React keys
  even when both represent the same research run.
- Format evidence-backfill timestamps with the active locale and explicit
  `Asia/Shanghai` time zone so server and browser text match.
- Preserve the homepage, five-day acceptance progress, and worktree metadata.
- Do not invoke refresh, discovery, outcome evaluation, backfill, assistant,
  watchlist, portfolio, order, or trading actions.

## Acceptance Criteria

- [x] Chinese component tests render coverage provider/date and outcome as-of
      labels without missing-message fallback.
- [x] A page regression proves the two run-backed sibling components have
      distinct keys.
- [x] A cross-zone component regression proves evidence timestamps do not
      inherit the host time zone.
- [x] Focused/full Web tests, TypeScript, JSON validation, Trellis validation,
      and diff checks pass.
- [x] A rebuilt local AI Research page reports no console errors or warnings.
- [ ] The task is committed, archived, journaled, and pushed.
