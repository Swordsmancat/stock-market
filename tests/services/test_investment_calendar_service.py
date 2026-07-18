from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.domain.models import (
    Base,
    EconomicCalendarEvent,
    OfficialDisclosure,
    Watchlist,
    WatchlistItem,
)
from packages.services.investment_calendar import get_investment_calendar_payload


def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def economic_event(index: int, scheduled_at: datetime) -> EconomicCalendarEvent:
    return EconomicCalendarEvent(
        provider="eastmoney",
        external_event_id=f"event-{index}",
        country="中国",
        name=f"指标 {index}",
        reference_period="7月",
        importance=index % 6,
        scheduled_at=scheduled_at,
        previous_value=Decimal("1.1"),
        forecast_value=Decimal("1.2"),
        actual_value=None,
        unit="%",
        source_url="https://data.eastmoney.com/cjsj/foreign_0_0.html",
        retrieved_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )


def test_economic_month_is_grouped_in_shanghai_and_not_capped_at_200():
    db = session()
    db.add_all(
        economic_event(index, datetime(2026, 7, 1 + index % 28, index % 16, tzinfo=timezone.utc))
        for index in range(260)
    )
    db.commit()

    payload = get_investment_calendar_payload(
        session=db, start=date(2026, 7, 1), end=date(2026, 7, 31)
    )

    assert payload["count"] == 260
    assert payload["truncated"] is False
    assert sum(day["count"] for day in payload["days"]) == 260
    assert payload["days"][0]["date"] == "2026-07-01"


def test_shanghai_day_boundaries_exclude_adjacent_local_dates():
    db = session()
    db.add_all(
        [
            economic_event(1, datetime(2026, 6, 30, 15, 59, tzinfo=timezone.utc)),
            economic_event(2, datetime(2026, 6, 30, 16, 0, tzinfo=timezone.utc)),
            economic_event(3, datetime(2026, 7, 31, 15, 59, tzinfo=timezone.utc)),
            economic_event(4, datetime(2026, 7, 31, 16, 0, tzinfo=timezone.utc)),
        ]
    )
    db.commit()

    payload = get_investment_calendar_payload(
        session=db, start=date(2026, 7, 1), end=date(2026, 7, 31)
    )

    assert payload["count"] == 2
    assert [day["date"] for day in payload["days"]] == ["2026-07-01", "2026-07-31"]


def test_company_events_are_scoped_to_active_cn_watchlist_symbols():
    db = session()
    watchlist = Watchlist(name="默认", is_default=True)
    db.add(watchlist)
    db.flush()
    db.add_all(
        [
            WatchlistItem(
                watchlist_id=watchlist.id,
                symbol="000001",
                market="CN",
                name="平安银行",
                is_active=True,
            ),
            WatchlistItem(
                watchlist_id=watchlist.id,
                symbol="600519",
                market="CN",
                name="贵州茅台",
                is_active=False,
            ),
        ]
    )
    for index, symbol in enumerate(("000001", "600519", "AAPL")):
        db.add(
            OfficialDisclosure(
                source="cninfo",
                source_document_id=f"doc-{index}",
                symbol=symbol,
                company_name=symbol,
                title=f"公告 {index}",
                category="年度报告",
                published_at=datetime(2026, 7, 16, index, tzinfo=timezone.utc),
                source_url=f"https://example.test/{index}",
                retrieved_at=datetime(2026, 7, 16, tzinfo=timezone.utc),
                dedupe_hash=str(index),
            )
        )
    db.commit()

    payload = get_investment_calendar_payload(
        session=db,
        start=date(2026, 7, 1),
        end=date(2026, 7, 31),
        kind="company",
        min_importance=5,
    )

    assert payload["count"] == 1
    assert payload["days"][0]["items"][0]["symbol"] == "000001"
    assert payload["days"][0]["items"][0]["importance"] is None


@pytest.mark.parametrize(
    ("start", "end", "kind", "importance"),
    [
        (date(2026, 7, 2), date(2026, 7, 1), "economic", 0),
        (date(2026, 1, 1), date(2026, 7, 1), "economic", 0),
        (date(2026, 7, 1), date(2026, 7, 31), "unknown", 0),
        (date(2026, 7, 1), date(2026, 7, 31), "economic", 6),
    ],
)
def test_request_validation(start, end, kind, importance):
    with pytest.raises(ValueError):
        get_investment_calendar_payload(
            session=session(),
            start=start,
            end=end,
            kind=kind,
            min_importance=importance,
        )
