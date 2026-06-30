from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.analytics.fundamentals import FundamentalSnapshot
from packages.services.fundamentals import upsert_fundamental_snapshot
from packages.shared.database import Base, get_session


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_fundamentals_api_returns_mock_metrics_with_citation():
    session = make_session()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.get("/fundamentals/AAPL", params={"as_of": "2026-01-20"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["source"] == "mock_fundamentals"
    assert payload["as_of"] == "2026-01-20"
    assert payload["citation"] == "fundamental_metrics:AAPL:2026-01-20"
    assert payload["item"]["pe_ratio"] == 28.4
    assert payload["item"]["revenue_growth"] == 0.08
    assert "PE 28.40" in payload["item"]["summary"]


def test_fundamentals_api_returns_database_metrics_when_available():
    session = make_session()
    upsert_fundamental_snapshot(
        FundamentalSnapshot(
            symbol="AAPL",
            as_of=date(2026, 1, 19),
            currency="USD",
            pe_ratio=30.5,
            revenue_growth=0.12,
            net_margin=0.25,
            debt_to_assets=0.29,
        ),
        session=session,
        source="test_fixture",
    )

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.get("/fundamentals/AAPL", params={"as_of": "2026-01-20"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["source"] == "database"
    assert payload["as_of"] == "2026-01-19"
    assert payload["citation"] == "fundamental_metrics:AAPL:2026-01-19"
    assert payload["item"]["pe_ratio"] == 30.5
