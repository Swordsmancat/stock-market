# Consolidate personal-use research workflow

## Goal

Turn the existing secondary modules into a focused personal A-share research
workflow while preserving the homepage information, composition, and behavior
that the user already values. Maintenance, diagnostics, and low-value
integration surfaces must not dominate the other modules. Preserve useful
backend capabilities and stored data while reducing visible complexity.

## Background

- The user reports that the homepage appears usable, while most secondary
  functions appear unusable and many are unnecessary for personal use.
- The user explicitly confirmed that the homepage information is satisfactory.
  Homepage content, section ordering, and data presentation are therefore a
  protected boundary rather than a redesign target.
- The normal local Web/API runtime, A-share coverage, and DeepSeek-backed stock
  discovery and market assistant have passed live acceptance.
- A route-by-route product and runtime audit was completed before scope was
  chosen, so render failures are separated from low-value or poorly connected
  workflows.
- Existing backend capabilities and data must not be deleted merely because a
  page is hidden or consolidated.
- The audit found 13 localized page routes. Every tested top-level route
  rendered successfully on the normal local stack without a persistent console
  error or horizontal overflow. The main failure is information architecture
  and low-value/default data, not missing route integration.
- Desktop and mobile currently expose the same flat 10-item primary navigation.
  Mobile places all ten items in a horizontally scrolling bottom bar.
- The audit recorded homepage no-data and mock-data boundaries, but the user
  chose to preserve the current homepage instead of addressing those findings
  in this task.
- The strongest working personal flow is the daily AI shortlist into the
  instrument detail page and cited market assistant. That flow is buried among
  evidence-coverage and backfill controls.
- The current watchlist contains test/index placeholders, portfolios are an MVP
  demo, reports default to AAPL, alerts are empty, and task runs expose raw
  operational payloads. These states explain why technically rendered pages do
  not feel usable.
- The user authorized one-time local cleanup of the two audited active
  watchlist placeholders. Cleanup must deactivate, not physically delete, the
  exact `TEST:US` and `CN_SHANGHAI_COMPOSITE:CN` rows and must not generalize
  into an automatic symbol-matching rule.
- Detailed evidence is recorded in `route-audit.md`.

## Requirements

### R1. Route and workflow audit

- Inventory every user-facing localized page and its navigation entry.
- Verify each page at desktop and mobile widths against the running local stack.
- Classify each surface as personal core, supporting configuration, advanced
  maintenance, redundant/low-value, or broken.
- For broken pages, record the visible failure and the failing UI/API boundary
  before proposing a fix.

### R2. Personal-use information architecture

- Keep the primary navigation small and organized around repeated personal
  research actions rather than backend modules.
- Preserve the homepage's existing content, section order, links, information
  density, and runtime behavior. Shared-shell navigation changes must not alter
  the homepage's main content.
- Move operational/diagnostic surfaces behind one clearly secondary entry or
  remove them from primary navigation without deleting their routes or data.
- The confirmed primary navigation is Home, AI Research, Instruments,
  Watchlist, and Settings.
- Reports and alert history are reached contextually from a stock or watchlist.
  Evidence and Task Runs are advanced maintenance routes. Portfolio remains
  directly addressable but is hidden from primary navigation.
- Remove the fake account/profile/logout affordances from the single-user shell.

### R3. Core workflow usability

- A user must be able to move from market overview to an AI-selected candidate,
  inspect that symbol's stored evidence, and ask a cited AI question without
  knowing internal task/provider concepts.
- Fix only blockers on retained core workflows. Do not expand every existing
  page to feature parity.
- Empty, unavailable, and degraded states must explain the actual data boundary
  and offer a useful next action when one exists.
- Put daily shortlist/discovery and cited analysis before coverage/backfill
  operations on AI Research.
- Put the assistant, price/evidence summary, technicals, fundamentals, and news
  before provider-unsupported depth/trades/fund-flow sections on stock detail.
- Make the stock list query/pagination-oriented rather than loading all 5,530
  instruments and fanning out latest/bar requests for arbitrary first rows.
- Keep independently available notes, briefs, and evidence visible when one
  Evidence-page aggregate fails; maintenance ingestion controls remain advanced.

### R4. Focused LLM settings

- Built-in DeepSeek/OpenAI presets should require only an API key; URL/model
  details remain automatic and visually secondary.
- Custom URL/model fields appear only for a custom OpenAI-compatible endpoint.
- A manual connection test may make one minimal request per click and returns
  only model, latency, and sanitized success/error state. It never runs on save,
  retries automatically, exposes secrets, or replaces a saved configuration on
  failure.

### R5. Personal-use boundary

- Do not add accounts, roles, collaboration, broker execution, portfolio
  accounting, multi-profile API configuration, or professional-terminal
  density.
- Do not delete backend integrations, migrations, evidence, or audit history as
  part of navigation simplification.
- Persisted personal rows must not be deleted or deactivated merely because they
  resemble test/demo data unless the user explicitly authorizes local cleanup.
- The authorized cleanup is limited to the two exact active watchlist rows
  recorded above. Reports, portfolios, task runs, research evidence, and other
  historical rows remain untouched.

## Acceptance Criteria

- [x] A checked route matrix records render/API status and product classification
      for every localized page on desktop and mobile.
- [x] Homepage main content, section order, information density, links, and data
      behavior remain unchanged apart from unavoidable shared-shell navigation.
- [x] The primary navigation exposes only the agreed personal core and one
      settings utility: Home, AI Research, Instruments, Watchlist, and Settings,
      with no dead links.
- [x] Reports and Alerts are contextual; Evidence and Task Runs are advanced;
      Portfolio is hidden from primary navigation while all routes/data remain.
- [x] The retained research workflow connects overview -> candidate -> evidence
      -> cited AI analysis using the existing local data and DeepSeek config.
- [x] AI Research and instrument detail present their personal research content
      before coverage, backfill, depth, trade, and provider-maintenance details.
- [x] Instruments use bounded server-side query/pagination and global search no
      longer downloads the complete 5,530-symbol universe on dialog open.
- [x] Evidence preserves independently available notes/briefs when one aggregate
      request fails, while ingestion controls are advanced rather than primary.
- [x] Secondary operational routes remain directly addressable unless a proven
      duplicate is intentionally redirected; no stored data is removed.
- [x] The two authorized watchlist placeholders are inactive after a recorded
      one-time cleanup; no other local rows are changed.
- [x] LLM preset configuration and one-click manual testing are usable without
      requiring a built-in provider URL/model or exposing the key.
- [x] Focused UI/API tests, TypeScript, affected Python checks, full web tests,
      route-level browser acceptance, and secret-safe evidence pass.

## Out of Scope

- Making every existing page a first-class personal workflow.
- Deleting backend services or database tables solely to simplify navigation.
- New data sources, screening rules, AI prompts, trading recommendations, or
  automated trading.
- A broad visual redesign unrelated to personal workflow clarity.
- Homepage content, cards, data selection, section ordering, and presentation.

