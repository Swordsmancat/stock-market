from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.domain.models import EconomicCalendarEvent, OfficialDisclosure, WatchlistItem


SHANGHAI = ZoneInfo("Asia/Shanghai")
MAX_CALENDAR_RANGE_DAYS = 42
MAX_CALENDAR_ITEMS = 2_500
CALENDAR_KINDS = {"economic", "company"}


def get_investment_calendar_payload(
    *,
    session: Session,
    start: date,
    end: date,
    kind: str = "economic",
    min_importance: int = 0,
) -> dict[str, object]:
    _validate_request(start=start, end=end, kind=kind, min_importance=min_importance)
    start_at, end_at = _utc_bounds(start, end)
    if kind == "economic":
        rows = list(
            session.scalars(
                select(EconomicCalendarEvent)
                .where(
                    EconomicCalendarEvent.scheduled_at >= start_at,
                    EconomicCalendarEvent.scheduled_at <= end_at,
                    EconomicCalendarEvent.importance >= min_importance,
                )
                .order_by(EconomicCalendarEvent.scheduled_at, EconomicCalendarEvent.id)
                .limit(MAX_CALENDAR_ITEMS + 1)
            )
        )
        items = [_economic_item(row) for row in rows[:MAX_CALENDAR_ITEMS]]
    else:
        active_cn_symbols = select(WatchlistItem.symbol).where(
            WatchlistItem.is_active.is_(True), WatchlistItem.market == "CN"
        )
        rows = list(
            session.scalars(
                select(OfficialDisclosure)
                .where(
                    OfficialDisclosure.published_at >= start_at,
                    OfficialDisclosure.published_at <= end_at,
                    OfficialDisclosure.symbol.in_(active_cn_symbols),
                )
                .order_by(OfficialDisclosure.published_at, OfficialDisclosure.id)
                .limit(MAX_CALENDAR_ITEMS + 1)
            )
        )
        items = [_company_item(row) for row in rows[:MAX_CALENDAR_ITEMS]]

    return {
        "status": "ok",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "kind": kind,
        "count": len(items),
        "truncated": len(rows) > MAX_CALENDAR_ITEMS,
        "days": _group_days(items),
    }


def _validate_request(*, start: date, end: date, kind: str, min_importance: int) -> None:
    day_count = (end - start).days + 1
    if day_count < 1 or day_count > MAX_CALENDAR_RANGE_DAYS:
        raise ValueError(f"date range must contain between 1 and {MAX_CALENDAR_RANGE_DAYS} days.")
    if kind not in CALENDAR_KINDS:
        raise ValueError("kind must be economic or company.")
    if not 0 <= min_importance <= 5:
        raise ValueError("min_importance must be between 0 and 5.")


def _utc_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(start, time.min, SHANGHAI).astimezone(timezone.utc),
        datetime.combine(end, time.max, SHANGHAI).astimezone(timezone.utc),
    )


def _group_days(items: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for item in items:
        grouped.setdefault(str(item["date"]), []).append(item)
    return [
        {
            "date": day,
            "count": len(day_items),
            "max_importance": max(
                (int(item["importance"]) for item in day_items if item["importance"] is not None),
                default=None,
            ),
            "items": day_items,
        }
        for day, day_items in grouped.items()
    ]


def _economic_item(item: EconomicCalendarEvent) -> dict[str, object]:
    scheduled = _as_shanghai(item.scheduled_at)
    return {
        "id": str(item.id),
        "kind": "economic",
        "date": scheduled.date().isoformat(),
        "time": scheduled.strftime("%H:%M"),
        "title": item.name,
        "importance": item.importance,
        "country": item.country,
        "symbol": None,
        "company_name": None,
        "category": None,
        "reference_period": item.reference_period,
        "previous": _decimal(item.previous_value),
        "forecast": _decimal(item.forecast_value),
        "actual": _decimal(item.actual_value),
        "unit": item.unit,
        "provider": item.provider,
        "source_url": item.source_url,
        "retrieved_at": _iso(item.retrieved_at),
    }


def _company_item(item: OfficialDisclosure) -> dict[str, object]:
    published = _as_shanghai(item.published_at)
    return {
        "id": str(item.id),
        "kind": "company",
        "date": published.date().isoformat(),
        "time": published.strftime("%H:%M"),
        "title": item.title,
        "importance": None,
        "country": None,
        "symbol": item.symbol,
        "company_name": item.company_name,
        "category": item.category,
        "reference_period": None,
        "previous": None,
        "forecast": None,
        "actual": None,
        "unit": None,
        "provider": item.source,
        "source_url": item.source_url,
        "retrieved_at": _iso(item.retrieved_at),
    }


def _as_shanghai(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(SHANGHAI)


def _iso(value: datetime) -> str:
    return _as_shanghai(value).isoformat()


def _decimal(value: Decimal | None) -> str | None:
    return None if value is None else str(value.normalize())
