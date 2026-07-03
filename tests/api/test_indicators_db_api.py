from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.services.ingestion import ingest_mock_market_snapshot
from packages.shared.database import Base, get_session


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_indicators_api_recalculates_and_reads_database_indicators():
    session = make_session()
    ingest_mock_market_snapshot("US", date(2026, 1, 1), date(2026, 1, 20), session=session)

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        recalculate_response = client.post(
            "/indicators/recalculate",
            params={
                "symbol": "AAPL",
                "start": "2026-01-01",
                "end": "2026-01-20",
                "ma_window": 3,
            },
        )
        indicators_response = client.get("/indicators/AAPL")
    finally:
        app.dependency_overrides.clear()

    assert recalculate_response.status_code == 200
    recalculate_payload = recalculate_response.json()
    assert recalculate_payload["status"] == "calculated"
    assert recalculate_payload["indicator_count"] == 6

    assert indicators_response.status_code == 200
    indicators_payload = indicators_response.json()
    assert indicators_payload["source"] == "database"
    assert indicators_payload["symbol"] == "AAPL"
    assert indicators_payload["as_of"] == "2026-01-20T00:00:00+00:00"
    assert set(indicators_payload["indicators"]) == {"ma", "rsi", "bollinger", "atr", "macd", "kdj"}
    assert indicators_payload["indicators"]["ma"] == 119.0
    assert indicators_payload["indicators"]["rsi"] == 100.0
    assert indicators_payload["indicators"]["bollinger"] == {
        "upper": 121.0,
        "middle": 119.0,
        "lower": 117.0,
    }
    assert indicators_payload["indicators"]["atr"] == 3.0
    assert set(indicators_payload["indicators"]["macd"]) == {"macd", "signal", "histogram"}
    assert isinstance(indicators_payload["indicators"]["macd"]["macd"], float)
    assert isinstance(indicators_payload["indicators"]["macd"]["signal"], float)
    assert isinstance(indicators_payload["indicators"]["macd"]["histogram"], float)
    assert set(indicators_payload["indicators"]["kdj"]) == {"k", "d", "j"}
    assert isinstance(indicators_payload["indicators"]["kdj"]["k"], float)
    assert isinstance(indicators_payload["indicators"]["kdj"]["d"], float)
    assert isinstance(indicators_payload["indicators"]["kdj"]["j"], float)
