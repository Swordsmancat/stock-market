from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import DailyBar, Instrument, Market
from packages.services.indicators import (
    calculate_and_store_daily_indicators,
    get_stored_indicators_payload,
)
from packages.services.ingestion import ingest_mock_market_snapshot
from packages.shared.database import Base


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed_daily_bars(
    session,
    symbol: str,
    rows: list[tuple[date, float, float, float, float]],
) -> None:
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
    for trade_date, open_price, high, low, close in rows:
        session.add(
            DailyBar(
                instrument_id=instrument.id,
                trade_date=trade_date,
                open=Decimal(str(open_price)),
                high=Decimal(str(high)),
                low=Decimal(str(low)),
                close=Decimal(str(close)),
                volume=Decimal("1000"),
            )
        )
    session.commit()


def test_calculates_and_stores_daily_indicators_from_ingested_bars():
    session = make_session()
    ingest_mock_market_snapshot("US", date(2026, 1, 1), date(2026, 1, 20), session=session)

    result = calculate_and_store_daily_indicators(
        "AAPL",
        date(2026, 1, 1),
        date(2026, 1, 20),
        session=session,
        ma_window=3,
    )
    payload = get_stored_indicators_payload("AAPL", session=session)

    assert result["status"] == "calculated"
    assert result["indicator_count"] == 8
    assert payload["source"] == "database"
    assert payload["symbol"] == "AAPL"
    assert payload["as_of"] == "2026-01-20T00:00:00+00:00"
    assert set(payload["indicators"]) == {
        "ma",
        "rsi",
        "bollinger",
        "atr",
        "macd",
        "kdj",
        "candlestick_patterns",
        "chip_distribution",
    }
    assert payload["indicators"]["ma"] == 119.0
    assert payload["indicators"]["rsi"] == 100.0
    assert payload["indicators"]["bollinger"] == {"upper": 121.0, "middle": 119.0, "lower": 117.0}
    assert payload["indicators"]["atr"] == 3.0
    assert set(payload["indicators"]["macd"]) == {"macd", "signal", "histogram"}
    assert isinstance(payload["indicators"]["macd"]["macd"], float)
    assert isinstance(payload["indicators"]["macd"]["signal"], float)
    assert isinstance(payload["indicators"]["macd"]["histogram"], float)
    assert set(payload["indicators"]["kdj"]) == {"k", "d", "j"}
    assert isinstance(payload["indicators"]["kdj"]["k"], float)
    assert isinstance(payload["indicators"]["kdj"]["d"], float)
    assert isinstance(payload["indicators"]["kdj"]["j"], float)
    candlestick_patterns = payload["indicators"]["candlestick_patterns"]
    assert candlestick_patterns["rule_set"] == "candlestick_patterns_v1"
    assert candlestick_patterns["integration_source"] == "instock_inspired_rules"
    assert candlestick_patterns["research_signal_only"] is True
    assert candlestick_patterns["pattern_count"] == 0
    assert candlestick_patterns["patterns"] == []
    chip_distribution = payload["indicators"]["chip_distribution"]
    assert chip_distribution["rule_set"] == "chip_distribution_v1"
    assert chip_distribution["integration_source"] == "instock_inspired_cyq"
    assert chip_distribution["research_signal_only"] is True
    assert chip_distribution["approximation"] == "volume_weighted_without_float_shares"
    assert chip_distribution["status"] == "evaluated"
    assert chip_distribution["evaluated_bars"] == 20
    assert chip_distribution["bucket_count"] == 60
    assert chip_distribution["benefit_ratio"] > 0
    assert chip_distribution["avg_cost"] is not None
    assert chip_distribution["cost_ranges"]["70"]["low"] <= chip_distribution["cost_ranges"]["70"]["high"]
    assert len(chip_distribution["top_buckets"]) <= 5


def test_stores_detected_candlestick_pattern_payload():
    session = make_session()
    seed_daily_bars(
        session,
        "PATTERN",
        [
            (date(2026, 1, 1), 9.0, 9.4, 8.8, 9.2),
            (date(2026, 1, 2), 10.0, 10.2, 8.8, 9.0),
            (date(2026, 1, 3), 8.8, 10.8, 8.7, 10.4),
        ],
    )

    result = calculate_and_store_daily_indicators(
        "PATTERN",
        date(2026, 1, 1),
        date(2026, 1, 3),
        session=session,
        ma_window=2,
    )
    payload = get_stored_indicators_payload("PATTERN", session=session)

    assert result["status"] == "calculated"
    candlestick_patterns = payload["indicators"]["candlestick_patterns"]
    assert candlestick_patterns["pattern_count"] == 1
    assert candlestick_patterns["patterns"] == [
        {
            "code": "bullish_engulfing",
            "label": "Bullish engulfing",
            "market_bias": "bullish",
            "lookback_bars": 2,
            "rule_set": "candlestick_patterns_v1",
        }
    ]
