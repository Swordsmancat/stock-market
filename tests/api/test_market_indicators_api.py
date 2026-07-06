import json
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.domain.models import MarketIndicatorObservation
from packages.services.market_indicators import (
    MarketIndicatorObservationSeed,
    get_latest_market_indicator_payload,
    seed_market_indicators,
    upsert_market_indicator_observation,
)
from packages.shared.database import Base, get_session


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def with_test_client(session):
    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def valid_seed_content(value="4.250000"):
    return json.dumps(
        {
            "observations": [
                {
                    "code": "us_10y_yield",
                    "as_of": "2026-07-03",
                    "value": value,
                    "source": "Audited seed: FRED DGS10",
                    "components": {
                        "source_series_id": "DGS10",
                        "methodology": "Daily 10-year Treasury constant maturity rate.",
                    },
                }
            ]
        }
    )


def test_market_indicator_seed_preview_api_validates_without_writing():
    session = make_session()
    client = with_test_client(session)
    try:
        response = client.post(
            "/market-indicators/seeds/preview",
            json={
                "content": valid_seed_content(),
                "filename": "macro-seeds.json",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "valid"
    assert payload["can_import"] is True
    assert payload["summary"]["inserts"] == 1
    assert payload["rows"][0]["code"] == "us_10y_yield"
    assert payload["rows"][0]["intent"] == "insert"
    assert session.query(MarketIndicatorObservation).count() == 0


def test_market_indicator_seed_import_api_rejects_invalid_content_atomically():
    session = make_session()
    content = json.dumps(
        [
            {
                "code": "us_10y_yield",
                "as_of": "2026-07-03",
                "value": "4.250000",
                "source": "Audited seed: FRED DGS10",
                "components": {"source_series_id": "DGS10"},
            }
        ]
    )
    client = with_test_client(session)
    try:
        response = client.post(
            "/market-indicators/seeds/import",
            json={"content": content, "format": "json"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    payload = response.json()
    assert payload["detail"]["status"] == "invalid"
    assert "components must include one of" in "; ".join(payload["detail"]["errors"])
    assert session.query(MarketIndicatorObservation).count() == 0


def test_market_indicator_seed_import_api_requires_overwrite_acknowledgement(monkeypatch):
    session = make_session()
    seed_market_indicators(session=session)
    upsert_market_indicator_observation(
        MarketIndicatorObservationSeed(
            code="us_10y_yield",
            as_of=date(2026, 7, 3),
            value=Decimal("4.250000"),
            source="Audited seed: FRED DGS10",
            components={
                "source_series_id": "DGS10",
                "methodology": "Initial reviewed value.",
            },
        ),
        session=session,
    )
    client = with_test_client(session)
    try:
        response = client.post(
            "/market-indicators/seeds/import",
            json={
                "content": valid_seed_content("4.310000"),
                "filename": "macro-seeds.json",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    payload = response.json()
    assert payload["detail"]["summary"]["updates"] == 1
    assert get_latest_market_indicator_payload("us_10y_yield", session=session)["value"] == 4.25

    monkeypatch.setattr(
        "apps.api.routers.market_indicators.clear_market_overview_cache",
        lambda provider_name=None: 7,
    )
    client = with_test_client(session)
    try:
        confirmed_response = client.post(
            "/market-indicators/seeds/import",
            json={
                "content": valid_seed_content("4.310000"),
                "filename": "macro-seeds.json",
                "overwrite_acknowledged": True,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert confirmed_response.status_code == 200
    confirmed_payload = confirmed_response.json()
    assert confirmed_payload["status"] == "imported"
    assert confirmed_payload["summary"] == {"inserts": 0, "updates": 1}
    assert confirmed_payload["cache"]["market_overview_cleared"] == 7
    assert get_latest_market_indicator_payload("us_10y_yield", session=session)["value"] == 4.31
