# Fix homepage news time and macro availability

## Goal

Make the personal homepage more useful without adding another module: show the
stored publication time for each latest-news row, remove the visible news
provider status strip, and restore real macro observations through the
existing audited official-source workflow.

## Requirements

- Show each latest-news item's `published_at` value using the active locale and
  the personal dashboard's `Asia/Shanghai` time zone. The timestamp must remain
  visible ahead of lower-priority source/confidence metadata inside the
  fixed-height panel. Missing or invalid values use the existing unavailable
  label.
- Remove the homepage panel titled `News source status` and its localized
  equivalent, including its page-only rendering helpers and translations.
  Provider capability data may still feed the existing aggregate AI sentiment
  health calculation.
- Preserve the current homepage layout, fixed middle-panel heights, scrolling,
  localization, research-only language, and stored-news-only read behavior.
- Do not fetch or write macro observations from a homepage GET. Macro values
  remain backed by audited local `MarketIndicatorObservation` rows.
- Raise the bounded World Bank request timeout so the existing official refresh
  can tolerate normal live API latency above ten seconds. Use the official
  `mrv` parameter with a bounded five-value window, then select the latest valid
  observation locally. Provider errors and their formatted exception chains
  must remain sanitized, and missing values must never become zero.
- After the code fix passes tests, run the existing World Bank dry-run and
  explicit write refresh for each Buffett target. This operational write is
  limited to audited public annual data and must clear the market-overview
  cache through the existing API path.
- Keep FRED-backed rates, inflation, and liquidity indicators as explicit
  `no_data` when `FRED_API_KEY` is not configured. Do not fabricate or scrape
  replacement values in this task.
- Preserve unrelated working-tree changes, especially the active five-day
  acceptance progress artifact and `.codex-worktrees/`.

## Acceptance Criteria

- [x] Latest stored-news rows display an `Asia/Shanghai` localized publication
      date and time, with a stable unavailable fallback.
- [x] The homepage no longer renders `News source status` in English or Chinese.
- [x] Existing latest-news failure, empty, bounded scrolling, and no-POST
      homepage contracts still pass.
- [x] The World Bank provider uses an official bounded `mrv=5` window and a
      tested bounded timeout that exceeds normal ten-second live latency while
      preserving latest-valid selection and fully sanitized failures.
- [x] Successful World Bank refresh writes audited Buffett observations; the
      market-overview payload exposes at least the successfully refreshed
      targets as `status=ok` without fabricated data.
- [x] Focused backend/frontend tests, web type-check, Trellis validation,
      `git diff --check`, and desktop/mobile browser checks pass.

## Notes

- Live diagnosis on 2026-07-16 initially found 9/9 overview macro rows at
  `no_data`, no local official observations, FRED unconfigured, and World Bank
  configured but empty. The original official `MRNEV` query is valid and means
  "most recent non-empty values", but reproduced timeout behavior even after
  45 seconds. A direct `mrv=5` comparison returned the USA 2021-2025 window
  within the bounded request budget; the service then selected 2025 locally.
- After correcting the parameter, explicit audited refreshes stored
  `buffett_indicator_cn=79.540605%` and
  `buffett_indicator_us=224.044649%`, both as of 2025-12-31. The market overview
  now reports both as `status=ok`. Hong Kong remains `no_data` after a sanitized
  upstream Request Error reproduced independently with `mrv=5`, and FRED-backed
  rows remain `no_data` because `FRED_API_KEY` is not configured.
- Final verification passed 358 frontend tests across 94 files, TypeScript,
  31 proportional World Bank/macro/dashboard backend tests, scoped Ruff, task
  validation, translation JSON parsing, and `git diff --check`. Desktop and
  mobile browser checks confirmed timestamp visibility, provider-panel absence,
  restored macro values, and no horizontal overflow.
