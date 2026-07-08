from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import DailyBar, FundamentalSnapshot, Instrument, Market, TechnicalIndicator
from packages.services.stock_selection import screen_local_stock_selection
from packages.shared.database import Base


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed_instrument(
    session,
    symbol: str,
    *,
    close: float,
    ma: float,
    rsi: float,
    pe_ratio: float = 25.0,
    revenue_growth: float = 0.12,
    net_margin: float = 0.24,
) -> None:
    market = session.query(Market).filter(Market.code == "US").one_or_none()
    if market is None:
        market = Market(code="US", name="US Stock", timezone="America/New_York", currency="USD")
        session.add(market)
        session.flush()
    instrument = Instrument(
        symbol=symbol,
        name=symbol,
        market=market,
        asset_type="stock",
        currency="USD",
    )
    session.add(instrument)
    session.flush()
    session.add(
        DailyBar(
            instrument_id=instrument.id,
            trade_date=date(2026, 1, 20),
            open=Decimal("100"),
            high=Decimal(str(close + 1)),
            low=Decimal("99"),
            close=Decimal(str(close)),
            volume=Decimal("1000000"),
        )
    )
    session.add(
        TechnicalIndicator(
            instrument_id=instrument.id,
            timeframe="1d",
            as_of=datetime(2026, 1, 20, tzinfo=timezone.utc),
            indicator_code="ma",
            params={"window": 20},
            value_json={"value": ma},
        )
    )
    session.add(
        TechnicalIndicator(
            instrument_id=instrument.id,
            timeframe="1d",
            as_of=datetime(2026, 1, 20, tzinfo=timezone.utc),
            indicator_code="rsi",
            params={"window": 14},
            value_json={"value": rsi},
        )
    )
    session.add(
        FundamentalSnapshot(
            symbol=symbol,
            as_of=date(2026, 1, 19),
            currency="USD",
            pe_ratio=Decimal(str(pe_ratio)),
            revenue_growth=Decimal(str(revenue_growth)),
            net_margin=Decimal(str(net_margin)),
            debt_to_assets=Decimal("0.30"),
            source="test_fixture",
        )
    )
    session.commit()


def test_stock_selection_matches_local_fundamental_and_technical_criteria():
    session = make_session()
    seed_instrument(session, "AAPL", close=110.0, ma=100.0, rsi=55.0)
    seed_instrument(session, "MSFT", close=90.0, ma=100.0, rsi=72.0, pe_ratio=42.0)

    payload = screen_local_stock_selection(
        session=session,
        symbols=["aapl", "MSFT", "AAPL"],
        max_pe_ratio=30.0,
        min_revenue_growth=0.10,
        min_net_margin=0.20,
        min_rsi=40.0,
        max_rsi=70.0,
        require_price_above_ma=True,
    )

    assert payload["status"] == "ok"
    assert payload["rule_set"] == "instock_composite_selection_v1"
    assert payload["research_signal_only"] is True
    assert payload["count"] == 1
    item = payload["items"][0]
    assert item["symbol"] == "AAPL"
    assert item["score"] == 1.0
    assert item["latest_bar"]["close"] == 110.0
    assert item["fundamentals"]["pe_ratio"] == 25.0
    assert item["technical_indicators"]["rsi"] == 55.0
    assert {rule["code"] for rule in item["matched_rules"]} == {
        "max_pe_ratio",
        "min_revenue_growth",
        "min_net_margin",
        "min_rsi",
        "max_rsi",
        "require_price_above_ma",
    }
    assert item["evidence_citations"] == [
        "bars_1d:AAPL:2026-01-20",
        "technical_indicators:AAPL:2026-01-20T00:00:00+00:00",
        "fundamental_metrics:AAPL:2026-01-19",
    ]
    assert any(
        diagnostic["symbol"] == "MSFT" and diagnostic["rule"] == "max_pe_ratio"
        for diagnostic in payload["diagnostics"]
    )


def test_stock_selection_requires_at_least_one_criterion():
    session = make_session()
    seed_instrument(session, "AAPL", close=110.0, ma=100.0, rsi=55.0)

    payload = screen_local_stock_selection(session=session, symbols=["AAPL"])

    assert payload["status"] == "invalid_request"
    assert payload["items"] == []
    assert payload["diagnostics"][0]["code"] == "NO_SELECTION_CRITERIA"


def test_stock_selection_reports_missing_fundamentals_without_fabricating_match():
    session = make_session()
    seed_instrument(session, "AAPL", close=110.0, ma=100.0, rsi=55.0)
    session.query(FundamentalSnapshot).delete()
    session.commit()

    payload = screen_local_stock_selection(
        session=session,
        symbols=["AAPL"],
        max_pe_ratio=30.0,
    )

    assert payload["status"] == "ok"
    assert payload["items"] == []
    assert payload["diagnostics"] == [
        {
            "symbol": "AAPL",
            "code": "MISSING_FUNDAMENTALS",
            "message": "Fundamental criteria were requested but no stored snapshot is available.",
        }
    ]
