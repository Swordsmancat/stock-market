from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.domain.models import Base, EconomicCalendarEvent
from packages.providers.eastmoney_economic_calendar import EconomicCalendarRecord
from packages.services.economic_calendar import (
    get_economic_calendar_payload,
    refresh_economic_calendar,
)
import pytest


def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def record(actual="1.2"):
    return EconomicCalendarRecord(
        "x",
        "i",
        "中国",
        "CPI",
        "6月",
        3,
        datetime(2026, 7, 1, 1, tzinfo=timezone.utc),
        None,
        Decimal("1.1"),
        Decimal(actual),
        "%",
        datetime.now(timezone.utc),
    )


def test_refresh_is_idempotent_and_updates_revisions():
    db = session()
    first = refresh_economic_calendar(
        session=db, start=date(2026, 7, 1), end=date(2026, 7, 1), fetcher=lambda *_: (record(),)
    )
    second = refresh_economic_calendar(
        session=db,
        start=date(2026, 7, 1),
        end=date(2026, 7, 1),
        fetcher=lambda *_: (record("1.3"),),
    )
    assert (first.inserted, second.updated) == (1, 1)
    assert db.query(EconomicCalendarEvent).count() == 1
    payload = get_economic_calendar_payload(
        session=db, start=date(2026, 7, 1), end=date(2026, 7, 1)
    )
    assert payload["items"][0]["actual"] == "1.3"


def test_provider_failure_preserves_existing_rows():
    db = session()
    refresh_economic_calendar(
        session=db, start=date(2026, 7, 1), end=date(2026, 7, 1), fetcher=lambda *_: (record(),)
    )
    with pytest.raises(RuntimeError):
        refresh_economic_calendar(
            session=db,
            start=date(2026, 7, 1),
            end=date(2026, 7, 1),
            fetcher=lambda *_: (_ for _ in ()).throw(RuntimeError("upstream")),
        )
    assert db.query(EconomicCalendarEvent).count() == 1


def test_refresh_deduplicates_repeated_source_occurrences():
    db = session()
    result = refresh_economic_calendar(
        session=db,
        start=date(2026, 7, 1),
        end=date(2026, 7, 1),
        fetcher=lambda *_: (record("1.2"), record("1.3")),
    )
    assert result.fetched == 1
    assert db.query(EconomicCalendarEvent).one().actual_value == Decimal("1.3")
