# Add stored Eastmoney industry ranking history

## Goal

Provide the screenshot-style industry gain ranking matrix for personal research:
top industries by daily percentage change across the latest 12 A-share trading
days, backed by stored observations rather than page-load scraping.

## Confirmed facts

- The repository already exposes current hot sectors and Eastmoney-derived
  fund-flow through AkShare, but it has no persisted per-industry daily ranking
  history.
- Eastmoney publishes the industry universe through `push2` and daily sector
  K-lines through `push2his`; AkShare wraps the same endpoints.
- Eastmoney Quote Center level-one industries are the canonical latest-market
  source: `gridlist.html#industry_board_1`, using universe filter `m:90 s:4`.
  Level-two/three or unrelated provider taxonomies must not be mixed into this
  stored history.
- On 2026-07-17, both the host and Docker runtime receive an immediate remote
  disconnect from `push2`, including browser-like TLS impersonation. AkShare
  fails at the same boundary. The public quote HTML itself remains reachable.
- Browser sessions and cookies must not be extracted automatically.

## Requirements

- Store normalized industry code, name, taxonomy, trade date, daily change
  percent, daily rank, provider, source and retrieval audit metadata.
- Default projection: Eastmoney industry taxonomy, top 20 per day, latest 12
  stored trading days, sorted by daily gain.
- Explicit bounded refresh only. GET and page load are database-only.
- Repeated refreshes are idempotent and may update a revised daily value/rank.
- Provider failure preserves stored history and returns a sanitized diagnostic.
- Add a compact localized ranking matrix to the macro research page, with
  configurable top count and day count within bounded limits.
- Provide gain-ladder and latest-day list views, ascending/descending order,
  top 10/20 and 5/10/12/20 trading-day controls, compact full-width layout,
  internal scrolling and distinct top-three rank badges.
- Keep unsupported taxonomy/level selectors visibly fixed rather than
  implying unavailable data, and do not invent hotspot or persistence icons.
- Attempt direct Eastmoney access first, then make at most one fallback attempt
  through an optional user-supplied HTTP(S) proxy.
- Accept an optional manually supplied Eastmoney Cookie. Treat both the proxy
  URL and Cookie as secrets: never echo their values through public settings,
  API diagnostics, logs, task artifacts or stored ranking rows.
- Do not use automated account login, CAPTCHA bypass, trading actions or model
  requests.

## Acceptance criteria

- [x] Provider fixtures cover universe access, daily K-line normalization,
  nulls, duplicates, and source failures.
- [x] Persistence/query tests cover idempotency, revisions and latest 12 trading days.
- [x] GET performs no network request and returns at most 20 x 20 stored cells.
- [x] Chinese and English ranking matrices render loaded, empty and failed states.
- [x] Ranking views, sorting, bounded count/day controls and responsive internal
  scrolling work without additional GET requests or page-level overflow.
- [ ] A permitted runtime access method completes a real refresh without
  exposing credentials or lowering data-integrity checks.
- [x] Full backend/Web/type/migration checks pass and 3000/8000 remain healthy.

Runtime note: the 2026-07-17 post-alignment direct probe is still rejected by
Eastmoney with sanitized code `EASTMONEY_INDUSTRY_REQUEST_FAILED`; no proxy or
Cookie is configured. The deployed API returns the canonical source/taxonomy
metadata from its database-only GET and preserves the empty/stored projection.
The final live-refresh criterion remains open until a permitted working access
path is available.
