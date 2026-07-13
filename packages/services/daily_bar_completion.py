from __future__ import annotations

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import DateTime, cast, func, text
from sqlalchemy.orm import Session

from packages.domain.models import DailyBar


SHANGHAI_TIMEZONE = ZoneInfo("Asia/Shanghai")
DAILY_BAR_COMPLETION_TIME = time(16, 0)


def completed_daily_bar_predicate(session: Session, bar=DailyBar):
    """Return the dialect-aware SQL predicate for a completed A-share daily bar."""
    dialect_name = session.get_bind().dialect.name
    if dialect_name == "sqlite":
        return func.datetime(bar.ingested_at) >= func.datetime(bar.trade_date, "+8 hours")
    if dialect_name == "postgresql":
        local_close = func.timezone(
            "Asia/Shanghai",
            cast(bar.trade_date, DateTime) + text("INTERVAL '16 hours'"),
        )
        return bar.ingested_at >= local_close
    raise RuntimeError("Daily-bar completion supports only SQLite and PostgreSQL.")


def daily_bar_timestamp_is_complete(ingested_at: datetime, trade_date: date) -> bool:
    """Apply the same completion rule in Python, treating naive timestamps as UTC."""
    local = _aware_utc(ingested_at).astimezone(SHANGHAI_TIMEZONE)
    return local.date() > trade_date or (
        local.date() == trade_date
        and local.timetz().replace(tzinfo=None) >= DAILY_BAR_COMPLETION_TIME
    )


def daily_bar_is_complete(bar: DailyBar) -> bool:
    return daily_bar_timestamp_is_complete(bar.ingested_at, bar.trade_date)


def as_shanghai_datetime(value: datetime) -> datetime:
    return _aware_utc(value).astimezone(SHANGHAI_TIMEZONE)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
