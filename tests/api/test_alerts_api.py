from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.services.alert_triggers import record_triggered_alerts, list_recent_alert_triggers_payload
from packages.shared.database import Base, get_session


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_record_triggered_alerts_persists_triggered_rules():
    session = make_session()
    record_triggered_alerts(
        "0700",
        "HK",
        {
            "triggered": True,
            "rules": [
                {"key": "price_above", "threshold": 400, "value": 420.5, "triggered": True},
            ],
        },
        session=session,
    )

    payload = list_recent_alert_triggers_payload(session=session)
    assert len(payload["items"]) == 1
    assert payload["items"][0]["symbol"] == "0700"
    assert payload["items"][0]["rule_key"] == "price_above"


def test_alerts_api_lists_recent_triggers():
    session = make_session()
    record_triggered_alerts(
        "AAPL",
        "US",
        {
            "triggered": True,
            "rules": [
                {"key": "rsi_below", "threshold": 30, "value": 25, "triggered": True},
            ],
        },
        session=session,
    )

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.get("/alerts/triggers/recent")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"][0]["symbol"] == "AAPL"
