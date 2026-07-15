# Fix homepage fund-flow scrolling

## Goal

Make every fund-flow row already loaded by the homepage reachable inside the
fixed-height desktop panel without changing the homepage information design or
adding product complexity.

## Background

At the `1280x720` desktop viewport, the fund-flow card has a client height of
about `226px` and a scroll height of about `301px`. Its outer card uses
`overflow-hidden`, while the `177px` content area has about `252px` of content
and `overflow-y: visible`. The excess is clipped and the user cannot scroll it.
The detail list also silently limits the already-loaded rows to four.

## Requirements

- Preserve the existing fund-flow chart, card header, action link, colors,
  formatting, empty state, data source, and homepage grid.
- In the fixed-height desktop layout, place the chart and detail rows in a
  vertical scroll region that supports mouse wheel, touch/pointer scrolling,
  and keyboard scrolling when focused.
- Give the scroll region an accessible name from the existing fund-flow
  heading and a visible focus state.
- Render every actionable fund-flow row already passed into the panel, subject
  to the panel's existing bounded row cap; do not silently stop at four rows.
- Keep smaller layouts naturally sized and prevent the panel change from
  introducing page-level horizontal overflow or nested-scroll interference.
- Do not change backend APIs, provider calls, homepage fetch limits, other
  panels, navigation, or five-day research acceptance behavior.

## Acceptance Criteria

- [x] A regression test fails before the fix because no named scroll region is
      present and the fifth loaded fund-flow row is absent from the panel list.
- [x] The fund-flow panel exposes one focusable region named by the existing
      heading and renders all currently loaded fund-flow rows.
- [x] At `1280x720`, the region has `overflow-y: auto`, its scroll height may
      exceed its client height, and an actual scroll interaction changes its
      scroll position while the card remains fixed-height.
- [x] At a `375px`-wide mobile viewport, the page has no horizontal overflow and
      the panel content remains reachable without breaking the main page scroll.
- [x] The homepage page test, full frontend suite, TypeScript check, Trellis validation,
      and browser console inspection pass.
- [ ] Only task-owned frontend/spec/task files are committed and pushed; the
      ongoing five-day acceptance is restored as the current task.

## Out of Scope

- Redesigning the homepage or changing the user's satisfied homepage content.
- Fetching more sectors, adding filters, changing fund-flow calculations, or
  introducing a custom scrollbar library.
- Changing other fixed-height dashboard panels in this task.
