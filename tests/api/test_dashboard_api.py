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


def test_dashboard_market_overview_api_returns_aggregated_payload():
    session = make_session()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.get("/dashboard/market-overview", params={"provider": "mock"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "mock"
    assert payload["range"]["timeframe"] == "1d"
    assert payload["followed"]["limit"] == 6
    assert payload["followed"]["items"][0]["symbol"] == "AAPL"
    assert len(payload["indices"]["items"]) == 10
    assert payload["indices"]["items"][0]["code"] == "cn_shanghai_composite"
    assert len(payload["valuation_indicators"]["items"]) == 3
    assert payload["valuation_indicators"]["items"][0]["code"] == "buffett_indicator_cn"
