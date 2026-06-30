from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
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
    assert result["indicator_count"] == 4
    assert payload["source"] == "database"
    assert payload["symbol"] == "AAPL"
    assert payload["as_of"] == "2026-01-20T00:00:00+00:00"
    assert payload["indicators"]["ma"] == 119.0
    assert payload["indicators"]["rsi"] == 100.0
    assert payload["indicators"]["bollinger"] == {"upper": 121.0, "middle": 119.0, "lower": 117.0}
    assert payload["indicators"]["atr"] == 3.0
