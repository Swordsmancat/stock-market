from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.domain.models import DailyBar, FundamentalSnapshot, Instrument, Market, TechnicalIndicator
from packages.shared.database import Base, get_session


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed_selection_fixture(session) -> None:
    market = Market(code="US", name="US Stock", timezone="America/New_York", currency="USD")
    session.add(market)
    session.flush()
    instrument = Instrument(
        symbol="AAPL",
        name="Apple Inc.",
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
            high=Decimal("112"),
            low=Decimal("99"),
            close=Decimal("110"),
            volume=Decimal("1000000"),
        )
    )
    session.add_all(
        [
            TechnicalIndicator(
                instrument_id=instrument.id,
                timeframe="1d",
                as_of=datetime(2026, 1, 20, tzinfo=timezone.utc),
                indicator_code="ma",
                params={"window": 20},
                value_json={"value": 100.0},
            ),
            TechnicalIndicator(
                instrument_id=instrument.id,
                timeframe="1d",
                as_of=datetime(2026, 1, 20, tzinfo=timezone.utc),
                indicator_code="rsi",
                params={"window": 14},
                value_json={"value": 55.0},
            ),
            TechnicalIndicator(
                instrument_id=instrument.id,
                timeframe="1d",
                as_of=datetime(2026, 1, 20, tzinfo=timezone.utc),
                indicator_code="mfi",
                params={"window": 14},
                value_json={"value": 62.0},
            ),
            TechnicalIndicator(
                instrument_id=instrument.id,
                timeframe="1d",
                as_of=datetime(2026, 1, 20, tzinfo=timezone.utc),
                indicator_code="william_r",
                params={"window": 14},
                value_json={"value": -24.0},
            ),
            TechnicalIndicator(
                instrument_id=instrument.id,
                timeframe="1d",
                as_of=datetime(2026, 1, 20, tzinfo=timezone.utc),
                indicator_code="candlestick_patterns",
                params={"rule_set": "candlestick_patterns_v1", "research_signal_only": True},
                value_json={
                    "value": {
                        "rule_set": "candlestick_patterns_v1",
                        "integration_source": "instock_inspired_rules",
                        "status": "evaluated",
                        "research_signal_only": True,
                        "pattern_count": 1,
                        "patterns": [
                            {
                                "code": "hammer",
                                "label": "Hammer",
                                "market_bias": "bullish",
                                "lookback_bars": 1,
                                "rule_set": "candlestick_patterns_v1",
                            }
                        ],
                    }
                },
            ),
            TechnicalIndicator(
                instrument_id=instrument.id,
                timeframe="1d",
                as_of=datetime(2026, 1, 20, tzinfo=timezone.utc),
                indicator_code="chip_distribution",
                params={
                    "rule_set": "chip_distribution_v1",
                    "research_signal_only": True,
                    "approximation": "volume_weighted_without_float_shares",
                },
                value_json={
                    "value": {
                        "rule_set": "chip_distribution_v1",
                        "research_signal_only": True,
                        "approximation": "volume_weighted_without_float_shares",
                        "status": "evaluated",
                        "benefit_ratio": 0.72,
                    }
                },
            ),
        ]
    )
    session.add(
        FundamentalSnapshot(
            symbol="AAPL",
            as_of=date(2026, 1, 19),
            currency="USD",
            pe_ratio=Decimal("25"),
            revenue_growth=Decimal("0.12"),
            net_margin=Decimal("0.24"),
            debt_to_assets=Decimal("0.30"),
            source="test_fixture",
        )
    )
    session.commit()


def test_stock_selection_api_screens_local_composite_criteria():
    session = make_session()
    seed_selection_fixture(session)

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.get(
            "/stock-selection/screen",
            params={
                "symbols": "aapl,AAPL",
                "market": "US",
                "max_pe_ratio": 30,
                "min_revenue_growth": 0.1,
                "min_rsi": 40,
                "max_rsi": 70,
                "require_price_above_ma": True,
                "required_pattern_codes": "hammer",
                "min_mfi": 50,
                "max_mfi": 70,
                "min_william_r": -50,
                "max_william_r": -10,
                "min_chip_benefit_ratio": 0.6,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["research_signal_only"] is True
    assert payload["count"] == 1
    assert payload["items"][0]["symbol"] == "AAPL"
    assert payload["items"][0]["research_signal_only"] is True
    assert payload["items"][0]["technical_indicators"]["mfi"] == 62.0
    assert payload["items"][0]["technical_indicators"]["william_r"] == -24.0
    assert payload["items"][0]["technical_indicators"]["chip_distribution"]["benefit_ratio"] == 0.72
    assert {rule["code"] for rule in payload["items"][0]["matched_rules"]} >= {
        "required_pattern_codes",
        "min_mfi",
        "max_mfi",
        "min_william_r",
        "max_william_r",
        "min_chip_benefit_ratio",
    }
    assert "buy" not in payload["disclaimer"].lower()
    assert payload["items"][0]["evidence_citations"] == [
        "bars_1d:AAPL:2026-01-20",
        "technical_indicators:AAPL:2026-01-20T00:00:00+00:00",
        "fundamental_metrics:AAPL:2026-01-19",
    ]


def test_stock_selection_api_rejects_empty_criteria():
    session = make_session()
    seed_selection_fixture(session)

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.get("/stock-selection/screen", params={"symbols": "AAPL"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "At least one fundamental or technical selection criterion is required."
