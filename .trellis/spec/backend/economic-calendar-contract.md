# Economic Calendar Contract

## 1. Scope / Trigger

An explicit personal-research refresh imports a bounded public economic release
calendar. Evidence Center reads must remain database-only. This contract does
not schedule work, scrape authenticated pages, trade, or invoke a model.

## 2. Signatures

- Provider: `fetch_eastmoney_economic_calendar(start, end) -> tuple[EconomicCalendarRecord, ...]`.
- Refresh: `refresh_economic_calendar(session, start, end, dry_run=False)`.
- Projection: `get_economic_calendar_payload(session, start, end, min_importance=0, country=None, limit=200)`.
- HTTP: `POST /economic-calendar/refresh` and `GET /economic-calendar/events`.

## 3. Contracts

- Refresh ranges contain 1-62 inclusive calendar days; reads return at most 200 rows.
- The public Eastmoney report is paged fully before any database mutation.
- Source clock values are interpreted as `Asia/Shanghai` and persisted as aware instants.
- Missing previous, forecast, or actual values remain null, never numeric zero.
- `(provider, external_event_id)` is unique; `MXID` is preferred and the fallback identity is deterministic.
- Repeated refreshes update revised values and never delete absent partial rows.
- Eastmoney importance is an integer from 0 through 5. Source pagination may
  repeat the same `MXID`; normalize all pages, keep the last occurrence, and
  upsert each unique identity once per transaction.
- Parse `PUBLISH_DATEH` before inspecting fallback fields. Only if it is
  unusable, combine the date portion of `PUBLISH_DATEH_Z` (which may include
  `00:00:00`) with `PUBLISH_DATETME`.
- GET and server page loads do not call a provider or write to the database.

## 4. Validation & Error Matrix

| Condition | Behavior |
| --- | --- |
| Range exceeds 62 days | HTTP 400; no provider call |
| Provider page fails or schema changes | HTTP 502 with bounded code; no stored change |
| Missing numeric source field | Store and return null |
| Same occurrence has revised actual | Update the existing row |
| Same `MXID` appears on multiple pages | Keep one normalized occurrence; no duplicate insert |
| `STAR` is 5 | Store and expose importance 5 |
| No stored matching rows | Return successful empty items |

## 5. Good / Base / Bad Cases

- Good: all pages normalize, one transaction upserts events, and the UI filters stored rows locally.
- Base: the month has no stored events and shows a truthful empty state with manual refresh.
- Bad: a GET route fetches Eastmoney, an upstream null becomes zero, or a partial page response replaces stored history.

## 6. Tests Required

- Provider tests cover pagination, exact Shanghai time, nulls, fallback identity, and failure shapes.
- SQLite service tests cover insert, revision update, idempotency, filtering, and failed-fetch preservation.
- API tests cover GET bounds and database-only empty reads.
- Web tests cover loaded/empty/refresh-failure behavior and the same-origin refresh proxy.

## 7. Wrong vs Correct

Wrong: fetch Eastmoney during page render and display raw upstream fields.

Correct: explicit POST -> normalized complete fetch -> transactional upsert -> bounded GET -> localized panel.
