# Fix homepage initial data, layout, and macro localization

## Goal

Make the personal homepage trustworthy and visually complete on first entry:
allow the cold market-overview read to finish, use the available desktop
height, and keep built-in macro indicator labels fully localized in Chinese.

## Background

- A read-only live reproduction at 1440x1000 showed the first
  `/dashboard/market-overview` call taking 6776 ms while the homepage aborts it
  after 5000 ms. The next two cached calls took 132 ms and 120 ms. The initial
  page therefore rendered 47 unavailable placeholders even though a reload
  exposed stored China/USA Buffett observations.
- With a successful overview read, the last dashboard row ended at y=816 in a
  1000 px viewport, leaving about 184 px unused. The main content already used
  the full available width, so the defect is fixed row height rather than a
  max-width container.
- The Chinese macro panel rendered backend English names and raw codes such as
  `Buffett Indicator - United States` and `buffett_indicator_us`.

## Requirements

- Give only `/dashboard/market-overview` a bounded 20-second server-read budget.
  Keep all other optional homepage reads on their existing five-second budget.
- Homepage reads remain GET-only. Do not trigger provider refresh, ingestion,
  backfill, observation writes, or fabricated fallback values from page entry.
- A successful response after more than five seconds must render its actual
  indices and stored macro observations instead of the failed empty projection.
  A failure after the 20-second bound must retain the existing explicit error
  banner and unavailable states.
- At the `xl` desktop breakpoint, arrange the six terminal modules as two
  columns and three rows so useful content fills the desktop viewport instead
  of leaving a large blank band below a compressed three-column grid.
- Preserve the single-column mobile flow, established panel dimensions and
  internal scrolling, keyboard focus rings, and no horizontal page overflow.
- Add localized English and Chinese labels for all nine built-in favorite
  macro indicator codes. The Chinese homepage must display those Chinese names
  and the English homepage must display the corresponding English names.
- Do not render raw macro indicator code subtitles on the homepage in either
  locale.
- Unknown/custom macro codes keep a bounded fallback to the stored display name
  or code; no backend/database names are rewritten.
- Preserve the existing terminal style, module ordering, links, data contracts,
  research-only language, and unrelated working-tree changes.

## Acceptance Criteria

- [x] A delayed market-overview response that arrives between 5 and 20 seconds
      is rendered on the first homepage request; no POST is issued.
- [x] Existing market-overview failure behavior still appears after the new
      bounded timeout.
- [x] On Chinese homepage fixtures, all nine built-in macro rows use Chinese
      names in both success and overview-failure projections, and the panel
      contains neither backend English names nor raw codes.
- [x] The English homepage retains readable English built-in labels without raw
      code subtitles.
- [x] At 1440x1000 and 1920x1080 with a successful overview response, the six
      modules form two columns with three distinct row tops and extend beyond
      the initial viewport bottom without page-level horizontal overflow.
- [x] At 1280x720, the news and fund-flow panels retain working internal
      vertical scrolling.
- [x] At 390x844, the page has no horizontal overflow, panels do not overlap,
      and mobile content remains normally scrollable.
- [x] Focused tests, full frontend tests, TypeScript, translation JSON parsing,
      Trellis validation, `git diff --check`, and desktop/mobile browser checks
      pass.

## Out Of Scope

- Automatic provider refresh or database writes on homepage entry.
- New macro sources, FRED credential setup, or fabrication for genuinely missing
  observations.
- Redesigning the homepage information architecture, palette, typography,
  navigation, or panel order.
