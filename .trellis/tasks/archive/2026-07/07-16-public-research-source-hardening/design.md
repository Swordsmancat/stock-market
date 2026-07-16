# Public research source hardening design

## Boundaries

This task changes two existing backend decision points without expanding the
product surface. Daily bars keep the current coordinator and response contract.
News keeps the current refresh route, persistence, and frontend state machine;
only the public CN adapter behind that route changes.

The provider boundary owns Eastmoney transport and wire-schema validation.
The news service owns candidate conversion, source order, persistence, and
diagnostics. Market-data service code owns database-versus-coordinator choice.

## Daily-bar flow

```text
GET exact CN daily bars
  -> load requested database rows
  -> select newest coherent provenance cohort
  -> minimum rows = min(35, max(1, ceil(requested weekdays / 2)))
  -> cohort sufficient and not mixed-incomplete: return database
  -> otherwise retain degraded database payload
  -> existing resilient coordinator with the required minimum rows
       requested source -> AkShare Eastmoney -> AkShare Sina -> Tushare
  -> first coherent sufficient source: return provider payload
  -> no sufficient source: return retained database payload + attempts
```

The threshold is intentionally a severe-sparsity detector rather than a claim
of exchange-calendar completeness. Half of weekdays tolerates holidays and
suspensions; the 35-row cap preserves the existing research-readiness scale.
The helper calculates weekday count arithmetically and does not add a calendar
dependency or iterate over unbounded date ranges.

Mixed-provenance recovery keeps its stronger existing stored boundary and row-
count requirements. Sparse coherent recovery uses only the bounded minimum row
count because exact requested start/end dates may be weekends or holidays.

## Public-news provider

`packages/providers/eastmoney_public_news.py` will expose a normalized provider
function and immutable item type. The provider owns:

- one constant HTTPS host/path;
- fixed callback, minimal public User-Agent/Accept/Referer headers, and fixed
  JSON search structure;
- `follow_redirects=False`, `trust_env=False`, configured timeout, one request,
  expected status/media type, and a 256 KiB parsing cap;
- exact callback wrapper and JSON object/result/list validation;
- bounded rows, required article code/title/date/publisher fields, plain-text
  extraction with `HTMLParser`, Asia/Shanghai publication time, and a fixed
  `https://finance.eastmoney.com/a/<code>.html` URL;
- sanitized enumerated errors only. Raw bodies, query payloads, headers, and
  exceptions do not cross the provider boundary.

The service adapter converts provider items into `NewsSearchCandidate` with
`provider="eastmoney_public"`. Publisher remains candidate/article `source`.
The existing candidate normalization performs the final symbol, URL, length,
sensitive-text, and persistence checks.

## Compatibility path

`ingest_akshare_news` remains as a callable compatibility name because existing
analysis routing and tests may reference it. Its implementation delegates to
the same public provider and returns `source="eastmoney_public"`; it no longer
imports or invokes `ak.stock_news_em`.

The current `akshare_enabled` platform flag controls whether refresh may call
the replacement adapter. This reuses the user's existing public-CN-source
choice and avoids adding another settings control in a personal-use UI.

## Error semantics

| Condition | Result |
| --- | --- |
| Sufficient coherent DB bars | Existing database response |
| Sparse DB, remote source succeeds | Existing provider response, source attempts visible |
| Sparse DB, remote sources fail/empty | Degraded retained DB response plus insufficient-coverage diagnostic |
| Public news valid empty list | Empty attempt; continue to yfinance |
| Timeout, redirect, status/media/schema/body error | Sanitized provider error; continue once |
| Public news persists rows | Stop and return refreshed stored projection |
| Public source disabled | No request; existing skipped diagnostic then yfinance |

## Rollout and rollback

- No database migration or frontend payload change is required.
- Validate provider and service behavior with injected transports before a
  single bounded live GET acceptance.
- Keep normal services running during development. Reload Web/API only after
  tests if runtime source changes are not auto-reloaded.
- Rollback is the scoped source commit. Stored normalized news remains valid
  evidence and does not need deletion.
- Fundamental placeholder correction is deliberately a follow-up because it
  needs a migration plus coverage recovery before safe production rollout.
