# Economic calendar data source

## Purpose

The Evidence Center economic calendar reads only stored PostgreSQL events. A
manual refresh imports a bounded public calendar range; opening the page never
scrapes or mutates data.

## Current source

| Field | Value |
| --- | --- |
| Provider | Eastmoney public data center |
| Report | `RPT_INFO_SCHEDULENEWSNEW` |
| Public page | `https://data.eastmoney.com/cjrl/` |
| API | `https://datacenter.eastmoney.com/securities/api/data/v1/get` |
| Authentication | None; no Cookie or account session |
| Adapter | `packages/providers/eastmoney_economic_calendar.py` |
| Storage | `economic_calendar_events` |
| Refresh | `POST /economic-calendar/refresh` (maximum 62 days) |
| Read | `GET /economic-calendar/events` (database-only, maximum 200 rows) |

## Normalized contract

The provider adapter owns upstream names and converts them into a stable event
record: occurrence identity, Shanghai scheduled time, country, indicator name,
importance, reference period, previous/forecast/actual values, and unit.
Missing numeric values remain `null`; they are never changed to zero. `MXID` is
preferred for identity, with a deterministic hash fallback.

## Replacement procedure

Implement another provider returning `EconomicCalendarRecord`, keep provider
network access in the explicit refresh service, and preserve the database/API
projection. Validate time zone, pagination, null values, identity, revisions,
and failure atomicity before switching the refresh adapter. Do not add provider
calls to GET routes or page rendering.

## Operations

Refresh the current month explicitly from the Evidence Center, or call:

```text
POST /economic-calendar/refresh
{"start":"2026-07-01","end":"2026-07-31","dry_run":false}
```

A failed upstream request writes nothing and keeps previously stored events.
