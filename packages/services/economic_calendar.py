from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.domain.models import EconomicCalendarEvent
from packages.providers.eastmoney_economic_calendar import (
    SOURCE_URL,
    EconomicCalendarRecord,
    fetch_eastmoney_economic_calendar,
)

SHANGHAI = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True)
class EconomicCalendarRefreshResult:
    fetched: int
    inserted: int
    updated: int
    dry_run: bool


def refresh_economic_calendar(
    *,
    session: Session,
    start: date,
    end: date,
    dry_run: bool = False,
    fetcher=fetch_eastmoney_economic_calendar,
) -> EconomicCalendarRefreshResult:
    records = tuple({record.external_event_id: record for record in fetcher(start, end)}.values())
    existing = (
        {
            item.external_event_id: item
            for item in session.scalars(
                select(EconomicCalendarEvent).where(
                    EconomicCalendarEvent.provider == "eastmoney",
                    EconomicCalendarEvent.external_event_id.in_(
                        [item.external_event_id for item in records]
                    ),
                )
            )
        }
        if records
        else {}
    )
    inserted = updated = 0
    now = datetime.now(timezone.utc)
    for record in records:
        item = existing.get(record.external_event_id)
        if item is None:
            item = EconomicCalendarEvent(
                provider="eastmoney", external_event_id=record.external_event_id, created_at=now
            )
            session.add(item)
            inserted += 1
        else:
            updated += 1
        _apply(item, record, now)
    if dry_run:
        session.rollback()
    else:
        session.commit()
    return EconomicCalendarRefreshResult(len(records), inserted, updated, dry_run)


def get_economic_calendar_payload(
    *,
    session: Session,
    start: date,
    end: date,
    min_importance: int = 0,
    country: str | None = None,
    limit: int = 200,
) -> dict[str, object]:
    if end < start or (end - start).days + 1 > 62:
        raise ValueError("date range must contain between 1 and 62 days.")
    if not 0 <= min_importance <= 5:
        raise ValueError("min_importance must be between 0 and 5.")
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200.")
    start_at = datetime.combine(start, time.min, SHANGHAI).astimezone(timezone.utc)
    end_at = datetime.combine(end, time.max, SHANGHAI).astimezone(timezone.utc)
    query = select(EconomicCalendarEvent).where(
        EconomicCalendarEvent.scheduled_at >= start_at,
        EconomicCalendarEvent.scheduled_at <= end_at,
        EconomicCalendarEvent.importance >= min_importance,
    )
    if country:
        query = query.where(EconomicCalendarEvent.country == country.strip())
    rows = list(session.scalars(query.order_by(EconomicCalendarEvent.scheduled_at).limit(limit)))
    countries = sorted({row.country for row in rows})
    return {
        "status": "ok",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "count": len(rows),
        "countries": countries,
        "items": [_payload(row) for row in rows],
    }


def _apply(item: EconomicCalendarEvent, record: EconomicCalendarRecord, now: datetime) -> None:
    item.indicator_id = record.indicator_id
    item.country = record.country
    item.name = record.name
    item.reference_period = record.reference_period
    item.importance = record.importance
    item.scheduled_at = record.scheduled_at
    item.previous_value = record.previous_value
    item.forecast_value = record.forecast_value
    item.actual_value = record.actual_value
    item.unit = record.unit
    item.source_url = SOURCE_URL
    item.metadata_json = {"report": "RPT_INFO_SCHEDULENEWSNEW", "timezone": "Asia/Shanghai"}
    item.retrieved_at = record.retrieved_at
    item.updated_at = now


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(SHANGHAI).isoformat()


def _value(value):
    return None if value is None else str(value.normalize())


def _payload(item: EconomicCalendarEvent) -> dict[str, object]:
    return {
        "id": str(item.id),
        "provider": item.provider,
        "external_event_id": item.external_event_id,
        "country": item.country,
        "name": item.name,
        "reference_period": item.reference_period,
        "importance": item.importance,
        "scheduled_at": _iso(item.scheduled_at),
        "previous": _value(item.previous_value),
        "forecast": _value(item.forecast_value),
        "actual": _value(item.actual_value),
        "unit": item.unit,
        "source_url": item.source_url,
        "retrieved_at": _iso(item.retrieved_at),
    }
