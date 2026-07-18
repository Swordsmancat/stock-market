# Market Research Information Architecture Acceptance

Date: 2026-07-18 (Asia/Shanghai)

## Information Architecture

- `/zh/evidence` and `/en/evidence` own macro indicators and macro evidence;
  neither route fetches or renders the economic calendar or industry history.
- `/zh/market-research` and `/en/market-research` own the stored economic
  calendar and Eastmoney industry ranking history.
- Both routes expose localized cross-links, and breadcrumbs use the localized
  Market Research label.
- The desktop sidebar exposes Market Research between Instruments and the
  lower-frequency personal research utilities. The mobile navigation remains
  the existing five destinations.

## Verification

- Focused Evidence/Market Research/navigation tests: 6 passed across 4 files.
- Full frontend suite: 433 passed across 118 files.
- TypeScript: passed with `--noEmit`.
- `/zh/market-research`: HTTP 200.
- API health: HTTP 200 on port 8000; Web remains healthy on port 3000.

Implementation commits: `4939bf5` and `6eca306`.
