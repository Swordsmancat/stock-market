from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.shared.database import Base, get_session


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_analysis_refresh_orchestrates_market_indicators_news_and_report():
    session = make_session()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.post(
            "/analysis/refresh",
            params={
                "symbol": "AAPL",
                "market": "US",
                "start": "2026-01-01",
                "end": "2026-01-20",
                "ma_window": 3,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["status"] == "refreshed"
    assert payload["ingestion"]["bar_count"] == 20
    assert payload["indicators"]["status"] == "calculated"
    assert payload["indicators"]["indicator_count"] == 2
    assert payload["news"]["status"] == "ingested"
    assert payload["news"]["sentiment_count"] == 1
    assert "MA 119.00" in payload["report"]["content_markdown"]
    assert "Apple reports strong growth in services revenue" in payload["report"]["content_markdown"]
    assert "technical_indicators:AAPL:2026-01-20T00:00:00+00:00" in payload["report"]["citations"]
    assert "news_articles:AAPL:https://example.com/aapl-services-growth" in payload["report"]["citations"]
