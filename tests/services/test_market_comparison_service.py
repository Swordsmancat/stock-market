from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from packages.domain.models import DailyBar, Exchange, Instrument, Market
from packages.services.market_comparison import (
    _finite_decimal,
    get_market_comparison_payload,
)
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
            asset_type="stock",
            currency="CNY",
        )
        for symbol, name in (
            ("600001", "Alpha Bank"),
            ("600002", "Beta Energy"),
            ("600003", "Gamma Tech"),
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
) -> None:
    value = Decimal(close)
    session.add(
        DailyBar(
            instrument_id=instrument.id,
            trade_date=trade_date,
            open=value,
            high=value,
            low=value,
            close=value,
            volume=Decimal("1000"),
            amount=Decimal("10000"),
            provider=provider,
            adjustment=adjustment,
            source=source,
            source_priority=0,
        )
    )


def test_market_comparison_normalizes_selection_and_searches_database_only():
    session = make_session()
    seed_instruments(session)
    session.commit()

    payload = get_market_comparison_payload(
        session=session,
        symbols=(" 600002 ", "600001", "600002"),
        query="Gamma",
    )

    assert payload["symbols"] == ["600002", "600001"]
    assert payload["status"] == "no_data"
    assert [item["symbol"] for item in payload["items"]] == ["600002", "600001"]
    assert [item["symbol"] for item in payload["search_results"]] == ["600003"]
    assert all(item["status"] == "no_data" for item in payload["items"])
    assert payload["data_mode"] == "stored"


def test_market_comparison_uses_coherent_series_and_exact_shared_dates():
    session = make_session()
    instruments = seed_instruments(session)
    for symbol, closes in (("600001", ("10", "11", "12")), ("600002", ("20", "18", "21"))):
        for day, close in zip((15, 16, 17), closes, strict=True):
            add_bar(session, instruments[symbol], date(2026, 7, day), close)
    add_bar(
        session,
        instruments["600001"],
        date(2026, 7, 14),
        "99",
        provider="other",
        adjustment="raw",
    )
    session.commit()

    payload = get_market_comparison_payload(
        session=session,
        symbols=("600002", "600001"),
        period="1m",
    )

    assert payload["status"] == "ok"
    assert payload["anchor_date"] == "2026-07-17"
    assert payload["shared_dates"] == ["2026-07-15", "2026-07-16", "2026-07-17"]
    assert payload["shared_date_count"] == 3
    assert [item["symbol"] for item in payload["items"]] == ["600002", "600001"]
    assert all(item["provider"] == "akshare" for item in payload["items"])
    assert all(item["adjustment"] == "qfq" for item in payload["items"])
    assert [bar["close"] for bar in payload["items"][1]["bars"]] == [10.0, 11.0, 12.0]


def test_market_comparison_reports_missing_symbols_without_replacement():
    session = make_session()
    instruments = seed_instruments(session)
    for symbol in ("600001", "600002"):
        add_bar(session, instruments[symbol], date(2026, 7, 16), "10")
        add_bar(session, instruments[symbol], date(2026, 7, 17), "11")
    session.commit()

    payload = get_market_comparison_payload(
        session=session,
        symbols=("600001", "999999", "600002"),
    )

    assert payload["status"] == "ok"
    assert payload["missing_symbols"] == ["999999"]
    assert "MISSING_REQUESTED_SYMBOLS" in payload["diagnostics"]
    assert [item["symbol"] for item in payload["items"]] == ["600001", "600002"]


def test_market_comparison_requires_two_shared_dates():
    session = make_session()
    instruments = seed_instruments(session)
    add_bar(session, instruments["600001"], date(2026, 7, 16), "10")
    add_bar(session, instruments["600002"], date(2026, 7, 17), "20")
    session.commit()

    payload = get_market_comparison_payload(
        session=session,
        symbols=("600001", "600002"),
    )

    assert payload["status"] == "no_data"
    assert payload["shared_date_count"] == 0
    assert "INSUFFICIENT_SHARED_DATES" in payload["diagnostics"]


def test_market_comparison_returns_explicit_empty_and_insufficient_states():
    session = make_session()
    seed_instruments(session)
    session.commit()

    empty = get_market_comparison_payload(session=session)
    insufficient = get_market_comparison_payload(session=session, symbols=("600001",))

    assert empty["status"] == "empty_selection"
    assert insufficient["status"] == "insufficient_selection"


def test_market_comparison_rejects_invalid_bounds_and_non_finite_numbers():
    session = make_session()
    seed_instruments(session)
    session.commit()

    try:
        get_market_comparison_payload(
            session=session,
            symbols=("1", "2", "3", "4", "5"),
        )
    except ValueError as exc:
        assert "at most four" in str(exc)
    else:
        raise AssertionError("Expected selection bound validation")

    assert _finite_decimal(Decimal("NaN")) is None
    assert _finite_decimal(Decimal("Infinity")) is None
    assert _finite_decimal(Decimal("10")) == Decimal("10")
