from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import apps.api.routers.market_daily_evidence as market_daily_evidence_router
import packages.services.market_daily_evidence as market_daily_evidence_service
from apps.api.main import app
from packages.domain.models import Base
from packages.shared.database import get_session


@pytest.fixture()
def client_and_session(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)()

    def override_session():
        yield testing_session

    app.dependency_overrides[get_session] = override_session
    monkeypatch.setattr(market_daily_evidence_router, "clear_market_overview_cache", lambda: True)
    try:
        yield TestClient(app), testing_session
    finally:
        app.dependency_overrides.clear()
        testing_session.close()
        Base.metadata.drop_all(engine)


def _stock_flow_payload():
    return {
        "status": "ok",
        "data_mode": "delayed",
        "source": "fake_stock_flow",
        "provider": "fake",
        "requested_provider": "fake",
        "effective_provider": "fake",
        "as_of": "2026-07-10T08:00:00+00:00",
        "market": "CN",
        "window": "today",
        "availability": {"status": "delayed"},
        "provider_capabilities": {"fund_flow": {"status": "delayed"}},
        "count": 1,
        "items": [
            {
                "symbol": "000001",
                "name": "Ping An Bank",
                "rank": 1,
                "main_net_flow_amount": 123.4,
                "provider": "fake",
                "source": "fake_stock_flow",
            }
        ],
    }


def test_import_and_list_market_daily_evidence(client_and_session, monkeypatch):
    client, _session = client_and_session
    calls = []

    def fake_loader(event_type, **kwargs):
        calls.append((event_type, kwargs))
        return _stock_flow_payload()

    monkeypatch.setattr(market_daily_evidence_service, "load_market_daily_evidence_payload", fake_loader)

    response = client.post(
        "/market-daily-evidence/import",
        json={
            "date": date(2026, 7, 10).isoformat(),
            "market": "CN",
            "provider": "fake",
            "event_types": ["stock_fund_flow"],
            "limit": 10,
        },
    )

    assert response.status_code == 200
    imported = response.json()
    assert imported["inserted"] == 1
    assert imported["updated"] == 0
    assert imported["cache"]["market_overview_cleared"] is True
    assert calls == [
        (
            "stock_fund_flow",
            {
                "trade_date": date(2026, 7, 10),
                "market": "CN",
                "provider_name": "fake",
                "limit": 10,
            },
        )
    ]

    listing_response = client.get(
        "/market-daily-evidence?event_type=stock_fund_flow&symbol=000001&date=2026-07-10&citable_only=true"
    )
    assert listing_response.status_code == 200
    listing = listing_response.json()
    assert listing["summary"]["total"] == 1
    assert listing["items"][0]["citation_id"] == (
        "market_daily_event:stock_fund_flow:000001:2026-07-10"
    )
    assert listing["citations"][0]["source_type"] == "market_daily_event"


def test_import_rejects_unsupported_event_type(client_and_session):
    client, _session = client_and_session

    response = client.post(
        "/market-daily-evidence/import",
        json={"event_types": ["unsupported"], "provider": "fake"},
    )

    assert response.status_code == 422
    assert "unsupported" in response.json()["detail"]["errors"][0]


def test_list_rejects_unsupported_event_type(client_and_session):
    client, _session = client_and_session

    response = client.get("/market-daily-evidence?event_type=unsupported")

    assert response.status_code == 422
    assert "unsupported" in response.json()["detail"]["errors"][0]
