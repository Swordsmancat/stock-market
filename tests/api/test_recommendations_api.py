from datetime import date, timedelta

from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers import recommendations as recommendations_router
from packages.services.market_data import MarketDataProviderUnavailableError
from packages.shared.database import get_session


def override_no_database_session():
    yield None


def build_strong_momentum_bars() -> list[dict[str, object]]:
    start_date = date(2026, 1, 1)
    stable_bars = [
        {
            "timestamp": (start_date + timedelta(days=day_index)).isoformat(),
            "close": 100.0 + day_index * 0.1,
            "volume": 1_000.0,
        }
        for day_index in range(26)
    ]
    momentum_closes = [100.0, 104.0, 108.0, 112.0]
    momentum_bars = [
        {
            "timestamp": (start_date + timedelta(days=26 + day_index)).isoformat(),
            "close": close,
            "volume": 1_000.0,
        }
        for day_index, close in enumerate(momentum_closes)
    ]
    return stable_bars + momentum_bars


def test_get_recommendations_uses_market_data_service(monkeypatch):
    service_calls: list[dict[str, object]] = []

    def fake_get_bars_payload(
        symbol,
        timeframe,
        start,
        end,
        session=None,
        provider_name=None,
    ):
        service_calls.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "session": session,
                "provider_name": provider_name,
            }
        )
        return {"items": build_strong_momentum_bars()}

    monkeypatch.setattr(
        recommendations_router.market_data_service,
        "get_bars_payload",
        fake_get_bars_payload,
    )

    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get(
            "/recommendations",
            params={"symbols": "aapl,AAPL,msft", "limit": 1, "provider": "mock"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["count"] == 1
    assert payload["items"][0]["symbol"] == "AAPL"
    assert payload["items"][0]["type"] == "strong_momentum"
    assert payload["items"][0]["confidence"] == 0.8
    assert payload["diagnostics"] == []
    assert [call["symbol"] for call in service_calls] == ["AAPL", "MSFT"]
    assert all(call["provider_name"] == "mock" for call in service_calls)


def test_get_recommendations_rejects_empty_symbols():
    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get("/recommendations", params={"symbols": " , "})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "At least one symbol is required"


def test_get_recommendations_reports_provider_failures(monkeypatch):
    def fake_get_bars_payload(
        symbol,
        timeframe,
        start,
        end,
        session=None,
        provider_name=None,
    ):
        raise MarketDataProviderUnavailableError("mock", "fetching bars", ConnectionError("down"))

    monkeypatch.setattr(
        recommendations_router.market_data_service,
        "get_bars_payload",
        fake_get_bars_payload,
    )

    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get("/recommendations", params={"symbols": "AAPL", "provider": "mock"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["count"] == 0
    assert payload["items"] == []
    assert payload["diagnostics"] == [
        {
            "symbol": "AAPL",
            "status": "provider_error",
            "category": "unavailable",
            "provider": "mock",
        }
    ]
