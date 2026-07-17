from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from packages.domain.models import DailyBar, Exchange, Instrument, Market
from packages.services.instrument_kline import get_instrument_kline_payload
from packages.services.stored_daily_bars import choose_daily_bar_cohort_key
from packages.shared.database import Base


def make_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed_instruments(session: Session) -> dict[str, Instrument]:
    market = Market(code="CN", name="China", timezone="Asia/Shanghai", currency="CNY")
    exchange = Exchange(market=market, code="SSE", name="SSE")
    instruments = {
        symbol: Instrument(
            symbol=symbol,
            name=name,
            market=market,
            exchange=exchange,
            asset_type=asset_type,
            currency="CNY",
            is_active=is_active,
        )
        for symbol, name, asset_type, is_active in (
            ("600001", "Alpha Bank", "stock", True),
            ("510300", "CSI 300 ETF", "etf", True),
            ("000300", "CSI 300", "index", True),
            ("900001", "Inactive", "stock", False),
            ("FUT1", "Unsupported Future", "future", True),
        )
    }
    session.add_all([market, exchange, *instruments.values()])
    session.flush()
    return instruments


def add_bar(
    session: Session,
    instrument: Instrument,
    trade_date: date,
    close: str,
    *,
    provider: str = "akshare",
    adjustment: str = "qfq",
    source: str = "eastmoney",
    high: str | None = None,
    low: str | None = None,
    volume: str = "1000",
) -> None:
    close_value = Decimal(close)
    session.add(
        DailyBar(
            instrument_id=instrument.id,
            trade_date=trade_date,
            open=close_value,
            high=Decimal(high) if high is not None else close_value,
            low=Decimal(low) if low is not None else close_value,
            close=close_value,
            volume=Decimal(volume),
            amount=Decimal("10000"),
            provider=provider,
            adjustment=adjustment,
            source=source,
            source_priority=0,
        )
    )


def test_catalog_is_database_only_filtered_and_stably_paginated():
    session = make_session()
    instruments = seed_instruments(session)
    add_bar(session, instruments["510300"], date(2026, 7, 17), "4.2")
    session.commit()

    first = get_instrument_kline_payload(session=session, limit=2)
    second = get_instrument_kline_payload(session=session, limit=2, offset=2)
    etfs = get_instrument_kline_payload(session=session, asset_type="etf", query="300")

    assert first["status"] == "empty"
    assert first["source"] == "database"
    assert first["total"] == 3
    assert first["has_more"] is True
    assert [item["symbol"] for item in first["catalog"]] == ["510300", "000300"]
    assert [item["symbol"] for item in second["catalog"]] == ["600001"]
    assert [item["symbol"] for item in etfs["catalog"]] == ["510300"]
    assert etfs["catalog"][0]["stored_bar_count"] == 1
    assert etfs["catalog"][0]["latest_bar"]["timestamp"] == "2026-07-17"


def test_selected_series_uses_one_coherent_cohort_and_period_anchor():
    session = make_session()
    instruments = seed_instruments(session)
    for day, close in ((15, "4.0"), (16, "4.1"), (17, "4.2")):
        add_bar(session, instruments["510300"], date(2026, 7, day), close)
    add_bar(
        session,
        instruments["510300"],
        date(2026, 7, 14),
        "99",
        provider="other",
        adjustment="raw",
    )
    session.commit()

    payload = get_instrument_kline_payload(
        session=session,
        symbol=" 510300 ",
        market=" cn ",
        period="1m",
    )

    assert payload["status"] == "ready"
    assert payload["selected"]["asset_type"] == "etf"
    assert payload["series"]["provider"] == "akshare"
    assert payload["series"]["adjustment"] == "qfq"
    assert payload["series"]["anchor_date"] == "2026-07-17"
    assert [item["close"] for item in payload["series"]["items"]] == [4.0, 4.1, 4.2]


def test_selected_series_drops_invalid_ohlcv_without_fabrication():
    session = make_session()
    instruments = seed_instruments(session)
    add_bar(session, instruments["000300"], date(2026, 7, 16), "10")
    add_bar(
        session,
        instruments["000300"],
        date(2026, 7, 17),
        "11",
        high="9",
        low="12",
    )
    session.commit()

    payload = get_instrument_kline_payload(
        session=session,
        symbol="000300",
        market="CN",
    )

    assert payload["status"] == "ready"
    assert payload["series"]["bar_count"] == 1
    assert payload["diagnostics"] == ["INVALID_STORED_BARS_DROPPED"]


def test_explicit_not_found_no_data_and_request_validation_states():
    session = make_session()
    seed_instruments(session)
    session.commit()

    not_found = get_instrument_kline_payload(
        session=session,
        symbol="999999",
        market="CN",
    )
    no_data = get_instrument_kline_payload(
        session=session,
        symbol="600001",
        market="CN",
    )

    assert not_found["status"] == "not_found"
    assert not_found["selected"] is None
    assert no_data["status"] == "no_data"
    assert no_data["selected"]["symbol"] == "600001"
    assert no_data["diagnostics"] == ["NO_STORED_DAILY_BARS"]

    for kwargs in (
        {"symbol": "600001"},
        {"asset_type": "future"},
        {"period": "5y"},
        {"limit": 51},
        {"offset": -1},
    ):
        try:
            get_instrument_kline_payload(session=session, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected request validation for {kwargs}")


def test_cohort_tie_break_is_lexical():
    assert choose_daily_bar_cohort_key(
        [("z_provider", "raw", 3), ("a_provider", "qfq", 3)]
    ) == ("a_provider", "qfq")
