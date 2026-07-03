from fastapi.testclient import TestClient

from apps.api.main import app
from packages.services import market_data as market_data_service
from packages.shared.database import get_session


def override_no_database_session():
    yield None


def test_get_intraday_returns_degraded_when_verified_minute_bars_are_unsupported():
    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get(
            "/market-data/AAPL/intraday",
            params={"date": "2026-07-03", "provider": "yfinance"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["timeframe"] == "1m"
    assert payload["date"] == "2026-07-03"
    assert payload["source"] == "none"
    assert payload["provider"] == "yfinance"
    assert payload["requested_provider"] == "yfinance"
    assert payload["effective_provider"] == "yfinance"
    assert payload["status"] == "degraded"
    assert payload["previous_close"] is None
    assert payload["items"] == []
    assert payload["availability"] == {
        "status": "degraded",
        "reason": market_data_service.INTRADAY_UNSUPPORTED_REASON,
        "is_realtime": False,
        "is_delayed": False,
        "delay_minutes": None,
    }


def test_get_intraday_uses_platform_default_provider_when_omitted(monkeypatch):
    monkeypatch.setattr(
        market_data_service,
        "get_effective_market_data_provider",
        lambda requested=None: "mock" if requested is None else str(requested).strip().lower(),
    )

    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get(
            "/market-data/AAPL/intraday",
            params={"date": "2026-07-03"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["requested_provider"] is None
    assert payload["effective_provider"] == "mock"
    assert payload["status"] == "degraded"
    assert payload["items"] == []


def test_get_intraday_rejects_unsupported_timeframes():
    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get(
            "/market-data/AAPL/intraday",
            params={"date": "2026-07-03", "timeframe": "5m", "provider": "mock"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported intraday timeframe: 5m. Only 1m is supported."
