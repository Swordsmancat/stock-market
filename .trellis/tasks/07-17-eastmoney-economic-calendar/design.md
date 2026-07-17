# Design

## Data flow

Eastmoney public report -> provider page normalizer -> explicit refresh service
-> `economic_calendar_events` -> GET projection -> Evidence Center server fetch
-> localized client panel. Only the explicit refresh path performs network and
database writes.

## Identity and time

Use `(provider, external_event_id)` as the unique occurrence identity. Prefer
Eastmoney `MXID`; if absent, derive a deterministic SHA-256 identity from the
indicator ID plus scheduled timestamp and name. Parse `PUBLISH_DATEH` first,
then `PUBLISH_DATEH_Z + PUBLISH_DATETME`; interpret the source clock as
`Asia/Shanghai` and persist a timezone-aware UTC instant.

## Provider bounds

The provider accepts inclusive `start`/`end`, rejects ranges over 62 days,
requests `pageSize=100`, and stops at the reported page count with a hard page
ceiling. The source-side filter is used only for dates because unsupported
filters may be silently ignored; importance/country filtering is performed on
normalized rows or the stored query.

## Persistence and revision behavior

Upsert every normalized occurrence. A later refresh may update scheduled time,
importance, values, name, and retrieval metadata for the same external event.
It never deletes events absent from a partial provider response. Refresh is one
transaction after a complete successful fetch; provider failure writes nothing.

## UI

The Evidence Center fetches stored current-month events in parallel with its
other independent reads. A client panel provides local country and importance
filters plus an explicit current-month refresh. It remains useful if other
Evidence Center reads fail and keeps operations out of the maintenance-only
provider tooling.
