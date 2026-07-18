# Real-data usability acceptance

Accepted on 2026-07-19 against the normal local PostgreSQL/API/Web stack. All
runtime probes were GET-only and no provider, crawler, ingestion, backfill,
assistant, watchlist, portfolio, order, or trading action was invoked.

## Module results

| Module | Result | Stored evidence | Classification |
| --- | --- | --- | --- |
| Market Movers | Pass | 2026-07-17 vs 2026-07-16; 5,518 comparable stocks; 481 gainers; `akshare/qfq` | Ready |
| Stock Comparison | Pass | `000001` and `600519`; 64 exact shared dates through 2026-07-17 | Selection required before data is shown; not a missing-data defect |
| Stock K-line | Pass | `000001`; 64 bars from 2026-04-15 through 2026-07-17; `akshare/qfq` | Ready |
| ETF K-line catalog | Data gap | 0 stored ETF identities | Catalog not collected |
| Index K-line catalog | Data gap | 0 stored index identities | Catalog not collected |

## Topic coverage

The four topic projections remained usable when individual sections were
empty. Counts below are stored matches in the 90-day window.

| Topic | News | Industry history | Companies | Latest evidence |
| --- | ---: | ---: | ---: | --- |
| Agriculture | 2 | 20 | 0 | 2026-07-17 |
| China consumption | 5 | 20 | 0 | 2026-07-17 |
| Real estate | 1 | 0 | 1 | 2026-07-09 |
| Non-ferrous metals | 5 | 0 | 0 | 2026-07-17 |

These are partial stored-evidence states, not page or database failures. No
missing section was filled with a fixture or live provider response.

## Product findings and fix

- Market Movers already exposed current dates, cohort provenance, and exact
  stored rows. No change was required.
- Stock Comparison already explained that two to four stored A-shares must be
  selected. The real two-stock workflow rendered metrics and correlations. No
  change was required.
- The K-line page previously treated a zero ETF/index catalog as a search miss
  and then prompted the user to choose an instrument. It now identifies the
  uncollected asset catalog and links to Data Storage and Crawler Monitor.
- Topic Research previously reused one generic empty description for news,
  industry history, and company metadata. Each section now states exactly
  which stored evidence category has no taxonomy/window match.
- API and database contracts were unchanged. Existing structured statuses and
  totals were sufficient, so no new backend or spec contract was introduced.

## Browser acceptance

- Chinese desktop pages rendered the corrected classifications with no console
  errors.
- At `390x844`, ETF empty coverage, a selected stock K-line, and Agriculture
  topic research had zero page-level horizontal overflow.
- The selected `000001` K-line rendered seven nonzero canvases. The primary
  chart canvases were 264 by 402 CSS/device pixels at the mobile viewport.

## Verification

- Focused page tests: 7 passed across the K-line and Topic Research pages.
- Full Web suite: 434 passed across 118 files.
- TypeScript: `npm.cmd exec tsc -- --noEmit -p apps/web/tsconfig.json` passed.
- English and Chinese locale JSON parsed successfully.
- Trellis validation and scoped `git diff --check` passed.

The smallest useful next data action is a separately authorized ETF/index
universe and daily-bar ingestion task. It is not required for these pages to
report their current storage state truthfully.
