# Acceptance: Homepage fund-flow scrolling

Date: 2026-07-15

## Reproduction

At `1280x720`, the original fund-flow card measured `226px` client height and
`301px` scroll height. Its `177px` content area had `252px` of content with
`overflow-y: visible`, while the card used `overflow-hidden`. The first focused
regression run failed because no accessible `Fund flow` region existed.

## Automated checks

- Focused homepage test after the fix: `5 passed`.
- Full frontend suite: `86` files and `279` tests passed.
- `npx tsc --noEmit -p apps/web/tsconfig.json`: passed.
- Trellis context validation and scoped diff checks: passed.
- No frontend linter is configured in this repository; no dependency or config
  was added solely for this small fix.

## Desktop browser

At `1280x720`, the card remained fixed at `226px`. The named focusable content
region measured `145px` client height and `292px` scroll height, with computed
`overflow-y: auto` and `tabIndex=0`. A real wheel action inside the panel moved
`scrollTop` from `0` to its maximum `147`. The visible desktop screenshot showed
the native panel scrollbar without overlap or layout shift.

## Mobile browser

At `375x812`, document client/scroll widths both measured `375px`. The card
expanded naturally to `389px`; its region measured `292px` client and scroll
height, so it did not create a nested mobile scroll. The main content remained
the vertical scroll owner (`755px` client height, `3858px` scroll height), and a
real scroll moved it from `0` to `1700`. Browser console warning/error count was
zero.

## Scope

The existing chart, labels, values, colors, action link, empty state, data
requests, and other homepage panels are unchanged. The list now exposes every
row already present in the bounded homepage payload.
