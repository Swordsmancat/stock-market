from datetime import date, timedelta

from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers import strategy_screening as strategy_screening_router
from packages.services.market_data import MarketDataProviderUnavailableError
from packages.shared.database import get_session


def override_no_database_session():
    yield None


def build_bar(day_index: int, close: float, *, volume: float = 1_000_000.0) -> dict[str, object]:
    timestamp = (date(2026, 1, 1) + timedelta(days=day_index)).isoformat()
    return {
        "timestamp": timestamp,
        "open": close,
        "high": close + 1,
        "low": close - 1,
        "close": close,
        "volume": volume,
    }


def build_turtle_breakout_bars() -> list[dict[str, object]]:
    bars = [build_bar(day_index, 100.0 + day_index * 0.1) for day_index in range(59)]
    bars.append(build_bar(59, 120.0))
    return bars


def test_strategy_screening_api_uses_market_data_service(monkeypatch):
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
                "start": start,
                "end": end,
                "provider_name": provider_name,
            }
        )
        return {
            "items": build_turtle_breakout_bars(),
            "source": "mock",
            "provider": "mock",
            "requested_provider": provider_name,
            "effective_provider": "mock",
        }

    monkeypatch.setattr(
        strategy_screening_router.market_data_service,
        "get_bars_payload",
        fake_get_bars_payload,
    )

    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get(
            "/strategies/screen",
            params={
                "symbols": "aapl,AAPL,msft",
                "strategies": "turtle_breakout",
                "start": "2026-01-01",
                "end": "2026-03-31",
                "provider": "mock",
                "limit": 1,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["research_signal_only"] is True
    assert payload["count"] == 1
    assert payload["items"][0]["symbol"] == "AAPL"
    assert payload["items"][0]["code"] == "turtle_breakout"
    assert payload["items"][0]["research_signal_only"] is True
    assert payload["symbols"][0]["source"] == "mock"
    assert payload["symbols"][0]["effective_provider"] == "mock"
    assert payload["diagnostics"] == []
    assert [call["symbol"] for call in service_calls] == ["AAPL", "MSFT"]
    assert all(call["provider_name"] == "mock" for call in service_calls)


def test_strategy_screening_api_rejects_bad_dates():
    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get(
            "/strategies/screen",
            params={
                "symbols": "AAPL",
                "start": "2026-04-01",
                "end": "2026-03-31",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "start must be on or before end"


def test_strategy_screening_api_reports_provider_failures(monkeypatch):
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
        strategy_screening_router.market_data_service,
        "get_bars_payload",
        fake_get_bars_payload,
    )

    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get("/strategies/screen", params={"symbols": "AAPL", "provider": "mock"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["items"] == []
    assert payload["diagnostics"] == [
        {
            "symbol": "AAPL",
            "status": "provider_error",
            "category": "unavailable",
            "provider": "mock",
        }
    ]
