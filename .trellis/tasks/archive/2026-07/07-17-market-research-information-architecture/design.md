# Design

## Boundaries

- Keep backend routes and provider/service code unchanged.
- Move only Web server fetch ownership and panel composition.
- Reuse `EconomicCalendarPanel` and `IndustryRankingHistoryPanel` directly.

## Route and data flow

- `/evidence`: macro-only fetch graph and macro evidence UI.
- `/market-research`: parallel database-only GET requests for calendar and
  industry history, then existing explicit POST refresh actions from panels.
- Cross-links are ordinary localized Next navigation links.

## Navigation decision

The desktop sidebar can accommodate Market Research as a sixth route and makes
the secondary surface directly discoverable. The primary mobile navigation
already has five personal high-frequency items, so the shared navigation item
is explicitly desktop-only there, avoiding a cramped sixth bottom-navigation
item. Macro Research cross-links and localized breadcrumbs remain available.

## Rollback

The new page and links can be removed and the two panel blocks restored to
`/evidence`; backend and stored data are unaffected.
