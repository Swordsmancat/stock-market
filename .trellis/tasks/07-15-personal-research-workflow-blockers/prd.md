# Fix personal research workflow blockers

## Goal

Fix the verified personal workflow blockers without expanding product scope: global search, shortlist evidence handoff, in-context watchlist action, and trustworthy financial states.

## Requirements

- Keep the protected homepage layout and content unchanged. Do not add reports,
  portfolio, trading, broker, or automated-investment capabilities.
- Restore global search in the real Next.js shell for both pointer activation
  and `Ctrl/Meta+K`, while retaining the existing bounded search request,
  localized loading/error states, keyboard dismissal, and result navigation.
- Preserve the selected instrument market in detail navigation whenever the
  source surface already knows it.
- Carry the immutable daily-shortlist identity as `symbol` plus an optional
  research snapshot ID from both shortlist entry points into the market
  assistant. The assistant must load the committed snapshot server-side,
  verify that the symbol belongs to it, consume structured supporting,
  opposing, gap, and invalidation evidence, and expose a citable snapshot
  reference. Do not copy snapshot arrays into URLs or visible questions.
- Do not render persisted free-text snapshot messages, labels, or explanation
  prose across locale boundaries. Build assistant context only from structured
  fields and codes.
- Add an in-context watch/unwatch control to instrument detail without
  resurfacing report generation or maintenance actions. Membership must be
  queried through a read-only endpoint that does not enrich prices, evaluate
  alerts, or write alert history. Unknown identity or membership must disable
  the control instead of guessing.
- Distinguish watchlist load failure from a genuinely empty watchlist and
  provide a localized recovery action.
- Format watchlist prices with the market currency (`CNY`, `HKD`, or `USD`)
  and render missing detail prices and movements as unavailable rather than
  synthetic zero values.
- Carry the exact optional `market` from search through instrument detail and
  the market assistant. For `market=CN` daily bars, use the requested provider
  first, then configured AkShare/Tushare sources when the primary source is
  empty, unavailable, rate-limited, or malformed. Never apply CN fallbacks to
  HK/US/unknown markets and never fall back to mock data.
- Keep database daily bars ahead of all provider calls and scope database
  identity by market when market is known. A successful fallback must expose
  the requested provider, effective provider, exact source, adjustment,
  fallback flag, and sanitized source attempts. Exhausted sources remain an
  explicit no-data/degraded state.
- Instrument detail and AI analysis must use the daily-bar effective provider,
  not the independently loaded market-depth provider. Show a localized source
  switch notice without exposing raw provider exceptions.
- Preserve existing watchlist alert rules, shortlist immutability, citation
  validation, no-trading safety behavior, and normal `3000`/`8000` services.
- Do not stage, commit, or alter the user's unrelated backend worktree changes.

## Acceptance Criteria

- [x] A clean Next.js browser run opens global search by click and by
      `Ctrl/Meta+K`; Escape closes it, and a result retains its market in the
      instrument-detail URL.
- [x] Selecting a daily shortlist candidate in the AI desk and opening its
      deep detail link both submit the exact snapshot ID to the assistant;
      selecting a normal/manual candidate clears any stale snapshot context.
- [x] Assistant tests prove the committed matching candidate contributes all
      four structured evidence groups and a `research_shortlist:` citation,
      while missing/mismatched snapshots produce explicit degraded diagnostics
      and raw persisted prose is not leaked.
- [x] Instrument detail shows a localized watch/unwatch control only for an
      exact resolved `(symbol, market)` identity and keeps the user on the same
      URL after mutation. Membership reads do not record alerts or mutate data.
- [x] Watchlist API failure renders an error state, a true empty payload renders
      the existing empty state, CN/HK/US values use their correct currencies,
      and missing values render the localized unavailable label.
- [x] Searching a CN instrument and opening detail forwards canonical
      `symbol + market`; yfinance empty/failure automatically selects the first
      configured valid AkShare/Tushare daily-bar source, records transparent
      provenance, and never calls mock or a CN source for HK/US/unknown markets.
- [x] Detail shows the actual daily-bar source switch, and its AI assistant
      forwards the same market plus daily-bar effective provider. A successful
      fallback produces normal price context/citations rather than
      `SOURCE_NO_DATA`; all-source exhaustion remains explicit and safe.
- [x] Focused frontend/backend tests, frontend type/lint checks, relevant full
      suites, and desktop/mobile browser checks pass without homepage changes.

## Notes

- This is a separately committed blocker-fix child of the ongoing five-day
  acceptance task. Evidence collection remains independent.
