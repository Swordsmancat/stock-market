# Validate exact-symbol search navigation

## Goal

Verify whether exact A-share symbol search fails to navigate from the homepage.

## Findings

- The search dialog opens and accepts `600519`.
- Both `/api/instruments` and the backend `/instruments` endpoint return one
  exact CN match.
- The client performs an asynchronous exact-market lookup and then navigates to
  `/zh/instruments/600519?market=CN`.
- The initial observation was taken before the SPA route transition completed;
  waiting for the target URL proved the workflow is functioning.
- No application code change is required.

## Acceptance Criteria

- [x] Exact-symbol API lookup returns one bounded result.
- [x] Browser search reaches the market-qualified detail URL.
- [x] No search regression or production error is present.
