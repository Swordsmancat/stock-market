from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import DailyBar, Exchange, Instrument, Market
from packages.services.daily_bar_completion import (
    completed_daily_bar_predicate,
    daily_bar_is_complete,
    daily_bar_timestamp_is_complete,
)
from packages.shared.database import Base


UTC = timezone.utc


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    database_session = sessionmaker(bind=engine)()
    try:
        yield database_session
    finally:
        database_session.close()
        Base.metadata.drop_all(engine)


def test_python_completion_boundary_treats_naive_timestamps_as_utc():
    trade_date = date(2026, 7, 10)

    assert not daily_bar_timestamp_is_complete(
        datetime(2026, 7, 10, 7, 59, 59),
        trade_date,
    )
    assert daily_bar_timestamp_is_complete(
        datetime(2026, 7, 10, 8, 0),
        trade_date,
    )
    assert daily_bar_timestamp_is_complete(
        datetime(2026, 7, 11, 0, 0, tzinfo=UTC),
        trade_date,
    )


def test_sqlite_predicate_matches_completion_boundary(session: Session):
    market = Market(
        code="CN",
        name="China A Share",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    session.add(market)
    session.flush()
    exchange = Exchange(market_id=market.id, code="SSE", name="SSE")
    session.add(exchange)
    session.flush()
    instrument = Instrument(
        symbol="600000",
        name="Test",
        market_id=market.id,
        exchange_id=exchange.id,
        asset_type="stock",
        currency="CNY",
        is_active=True,
    )
    session.add(instrument)
    session.flush()

    values = (
        (date(2026, 7, 8), datetime(2026, 7, 8, 7, 59, 59)),
        (date(2026, 7, 9), datetime(2026, 7, 9, 8, 0)),
        (date(2026, 7, 10), datetime(2026, 7, 11, 0, 0)),
    )
    for trade_date, ingested_at in values:
        session.add(
            DailyBar(
                instrument_id=instrument.id,
                trade_date=trade_date,
                open=Decimal("10"),
                high=Decimal("11"),
                low=Decimal("9"),
                close=Decimal("10"),
                volume=Decimal("100"),
                ingested_at=ingested_at,
            )
        )
    session.commit()

    completed_dates = session.scalars(
        select(DailyBar.trade_date)
        .where(completed_daily_bar_predicate(session, DailyBar))
        .order_by(DailyBar.trade_date)
    ).all()

    assert completed_dates == [date(2026, 7, 9), date(2026, 7, 10)]
    assert daily_bar_is_complete(session.get(DailyBar, (instrument.id, date(2026, 7, 9))))


def test_postgresql_predicate_is_session_timezone_independent():
    fake_session = SimpleNamespace(
        get_bind=lambda: SimpleNamespace(dialect=postgresql.dialect())
    )

    expression = completed_daily_bar_predicate(fake_session, DailyBar)
    compiled = str(
        expression.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "timezone" in compiled
    assert "Asia/Shanghai" in compiled
    assert "INTERVAL '16 hours'" in compiled


def test_completion_predicate_rejects_unsupported_dialects():
    fake_session = SimpleNamespace(
        get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="mysql"))
    )

    with pytest.raises(RuntimeError, match="only SQLite and PostgreSQL"):
        completed_daily_bar_predicate(fake_session, DailyBar)
