from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from packages.domain.models import DailyBar, Exchange, Instrument, Market
from packages.services.market_movers import _finite_decimal, get_market_movers_payload
from packages.shared.database import Base


def make_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed_market(session: Session) -> dict[str, tuple[Instrument, Exchange]]:
    market = Market(code="CN", name="China", timezone="Asia/Shanghai", currency="CNY")
    exchanges = {
        code: Exchange(market=market, code=code, name=code)
        for code in ("SSE", "SZSE", "BSE")
    }
    instruments = {
        "600001": Instrument(symbol="600001", name="Alpha", market=market, exchange=exchanges["SSE"], asset_type="stock", currency="CNY"),
        "000001": Instrument(symbol="000001", name="Beta", market=market, exchange=exchanges["SZSE"], asset_type="stock", currency="CNY"),
        "830001": Instrument(symbol="830001", name="Gamma", market=market, exchange=exchanges["BSE"], asset_type="stock", currency="CNY"),
        "600002": Instrument(symbol="600002", name="Delta", market=market, exchange=exchanges["SSE"], asset_type="stock", currency="CNY"),
    }
    session.add_all([market, *exchanges.values(), *instruments.values()])
    session.flush()
    return {symbol: (instrument, instrument.exchange) for symbol, instrument in instruments.items()}


def add_bar(
    session: Session,
    instrument: Instrument,
    trade_date: date,
    close: str,
    *,
    provider: str = "akshare",
    source: str = "eastmoney",
    adjustment: str = "qfq",
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
            source=source,
            adjustment=adjustment,
            source_priority=0,
        )
    )


def test_market_movers_uses_exact_latest_two_dates_and_dominant_cohort():
    session = make_session()
    rows = seed_market(session)
    for symbol, previous, current in (
        ("600001", "10", "12"),
        ("000001", "10", "11"),
    ):
        add_bar(session, rows[symbol][0], date(2026, 7, 16), previous)
        add_bar(session, rows[symbol][0], date(2026, 7, 17), current)
    add_bar(session, rows["830001"][0], date(2026, 7, 16), "10", provider="other")
    add_bar(session, rows["830001"][0], date(2026, 7, 17), "20", provider="other")
    add_bar(session, rows["600002"][0], date(2026, 7, 15), "1")
    add_bar(session, rows["600002"][0], date(2026, 7, 17), "100")
    session.commit()

    payload = get_market_movers_payload(session=session, direction="gainers", limit=10)

    assert payload["status"] == "ok"
    assert payload["trade_date"] == "2026-07-17"
    assert payload["previous_trade_date"] == "2026-07-16"
    assert payload["provider"] == "akshare"
    assert payload["adjustment"] == "qfq"
    assert [item["symbol"] for item in payload["items"]] == ["600001", "000001"]
    assert payload["omitted_count"] == 1


def test_market_movers_filters_exchange_and_orders_losers_stably():
    session = make_session()
    rows = seed_market(session)
    for symbol, previous, current in (
        ("600001", "10", "9"),
        ("600002", "20", "18"),
        ("000001", "10", "5"),
    ):
        add_bar(session, rows[symbol][0], date(2026, 7, 16), previous)
        add_bar(session, rows[symbol][0], date(2026, 7, 17), current)
    session.commit()

    payload = get_market_movers_payload(
        session=session,
        direction="losers",
        exchange="SSE",
        limit=10,
    )

    assert [item["symbol"] for item in payload["items"]] == ["600002", "600001"]
    assert all(item["exchange"] == "SSE" for item in payload["items"])


def test_market_movers_omits_invalid_previous_close():
    session = make_session()
    rows = seed_market(session)
    add_bar(session, rows["600001"][0], date(2026, 7, 16), "0")
    add_bar(session, rows["600001"][0], date(2026, 7, 17), "12")
    add_bar(session, rows["000001"][0], date(2026, 7, 16), "10")
    add_bar(session, rows["000001"][0], date(2026, 7, 17), "11")
    session.commit()

    payload = get_market_movers_payload(session=session, limit=10)

    assert [item["symbol"] for item in payload["items"]] == ["000001"]
    assert payload["omitted_count"] == 1
    assert payload["comparable_count"] == 1


def test_market_movers_returns_no_data_without_two_trade_dates():
    session = make_session()
    rows = seed_market(session)
    add_bar(session, rows["600001"][0], date(2026, 7, 17), "12")
    session.commit()

    payload = get_market_movers_payload(session=session, limit=20)

    assert payload["status"] == "no_data"
    assert payload["items"] == []
    assert payload["trade_date"] is None


def test_market_movers_rejects_non_finite_numeric_values():
    assert _finite_decimal(Decimal("NaN")) is None
    assert _finite_decimal(Decimal("Infinity")) is None
    assert _finite_decimal(Decimal("-Infinity")) is None
    assert _finite_decimal(Decimal("1000")) == Decimal("1000")


def test_market_movers_selects_the_largest_coherent_cohort():
    session = make_session()
    rows = seed_market(session)
    add_bar(session, rows["600001"][0], date(2026, 7, 16), "10", provider="coherent")
    add_bar(session, rows["600001"][0], date(2026, 7, 17), "12", provider="coherent")
    for symbol in ("000001", "830001"):
        add_bar(session, rows[symbol][0], date(2026, 7, 17), "20", provider="latest_only")
    session.commit()

    payload = get_market_movers_payload(session=session, limit=10)

    assert payload["provider"] == "coherent"
    assert [item["symbol"] for item in payload["items"]] == ["600001"]
