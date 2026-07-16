# Homepage news time and macro availability design

## Boundaries

This task changes one server-rendered homepage component plus the existing
World Bank provider request budget and bounded recent-value window. It does not
add a scheduler, live homepage fetch, new macro source, database schema,
citation type, or trading behavior.

## Data Flow

```text
Stored News.published_at -> /news/latest -> shared news decoder -> homepage time

World Bank public API -> existing official refresh service
  -> audited MarketIndicatorObservation -> market-overview cache/payload
  -> homepage macro favorites and existing AI citation gate
```

## Frontend Design

- Reuse `StoredNewsItem.published_at`; do not introduce a second payload type.
- Add a page-local date-time formatter using `Intl.DateTimeFormat`, the existing
  safe locale resolver, and explicit `Asia/Shanghai` time-zone conversion so
  server/container defaults cannot shift the displayed date.
- Put the timestamp first in the news row's secondary metadata line with
  `shrink-0`, followed by truncatable identity and confidence text. This keeps
  time visible in the fixed 15.5rem panel on narrow and desktop layouts.
- Remove `NewsProviderStatusStrip`, its page-only helper functions, unused
  imports, its render call, and only the translations owned by that strip.
- Retain provider capability loading because the existing aggregate AI
  sentiment calculation consumes it.

## Macro Reliability Design

- Keep the provider's timeout bounded, but increase its default from 10 to 30
  seconds. Live probes showed official requests can exceed ten seconds while a
  targeted request can still succeed normally.
- Use World Bank's documented `mrv` query parameter with the existing bounded
  five-value constant. `MRNEV` is also official, but live comparison showed that
  path exceeding 45 seconds while `mrv=5` returned a complete recent window.
- Keep `latest_only` selection in the service after the provider has skipped
  null/invalid rows. This preserves latest-valid behavior instead of trusting a
  single `mrv=1` row that could be empty for a lagged annual series.
- Keep current exception sanitization, audit metadata validation, dry-run
  rollback, observation upsert, and cache clearing unchanged.
- Suppress raw upstream exception chaining after creating the sanitized
  `WorldBankProviderError`; formatted tracebacks must not recover provider
  response text or credential-like values.
- Do not retry automatically inside the provider in this slice. A longer single
  attempt is easier to reason about and avoids multiplying public API traffic.
- Populate current local evidence only through explicit existing refresh API
  calls after tests pass. Run targets independently so one slow country cannot
  prevent other valid audited observations from being stored.

## Compatibility And Rollback

- News payload and backend endpoint contracts are unchanged. The World Bank
  change keeps the internal provider/service signatures and expands only the
  default latest query from one recent row to the existing five-row bound.
- Macro observations remain annual and lagged, not realtime.
- Rollback restores the prior provider timeout/recent-value behavior and news
  panel markup; stored World Bank observations remain valid audited evidence
  and need no rollback.
