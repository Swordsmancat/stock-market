from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.analytics.fundamentals import FundamentalSnapshot
from packages.providers.eastmoney_public_fundamentals import (
    EastmoneyPublicCompany,
    EastmoneyPublicFundamentalsSnapshot,
)
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


def test_fundamentals_api_returns_additive_public_company_context(monkeypatch):
    session = make_session()
    snapshot = EastmoneyPublicFundamentalsSnapshot(
        symbol="600519",
        as_of=date(2026, 6, 30),
        currency="CNY",
        pe_ratio=None,
        revenue_growth=0.125,
        net_margin=0.5125,
        debt_to_assets=0.1875,
        company=EastmoneyPublicCompany(
            name="Kweichow Moutai",
            industry="Beverage manufacturing",
            business_scope="Production and sale of spirits.",
            profile="Premium spirits producer.",
        ),
        status="ok",
        provider="eastmoney_public",
        upstream_sources=(
            "eastmoney.RPT_F10_FINANCE_MAINFINADATA",
            "eastmoney.PC_HSF10.CompanySurvey.PageAjax",
        ),
        retrieved_at=datetime(2026, 7, 16, tzinfo=timezone.utc),
        diagnostics=(),
    )
    monkeypatch.setattr(
        "packages.services.fundamentals.get_platform_settings",
        lambda: {"akshare_enabled": True},
    )
    monkeypatch.setattr(
        "packages.services.fundamentals.redis_client.get",
        lambda _key: None,
    )
    monkeypatch.setattr(
        "packages.services.fundamentals.redis_client.set",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        "packages.services.fundamentals.fetch_eastmoney_public_fundamentals",
        lambda *_args, **_kwargs: snapshot,
    )

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        response = TestClient(app).get(
            "/fundamentals/600519",
            params={"as_of": "2026-07-16"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["provider"] == "eastmoney_public"
    assert payload["item"]["pe_ratio"] is None
    assert payload["item"]["company"]["name"] == "Kweichow Moutai"
    assert payload["upstream_sources"] == list(snapshot.upstream_sources)
