from datetime import date, timedelta

from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers import strategy_screening as strategy_screening_router
from packages.services.market_data import MarketDataProviderUnavailableError
from packages.shared.database import get_session


def override_no_database_session():
    yield None


def build_bar(
    day_index: int,
    close: float,
    *,
    open_price: float | None = None,
    volume: float = 1_000_000.0,
    amount: float | None = None,
) -> dict[str, object]:
    timestamp = (date(2026, 1, 1) + timedelta(days=day_index)).isoformat()
    open_value = close if open_price is None else open_price
    bar: dict[str, object] = {
        "timestamp": timestamp,
        "open": open_value,
        "high": max(open_value, close) + 1,
        "low": min(open_value, close) - 1,
        "close": close,
        "volume": volume,
    }
    if amount is not None:
        bar["amount"] = amount
    return bar


def build_turtle_breakout_bars() -> list[dict[str, object]]:
    bars = [build_bar(day_index, 100.0 + day_index * 0.1) for day_index in range(59)]
    bars.append(build_bar(59, 120.0))
    return bars


def build_volume_price_breakout_evaluation_bars() -> list[dict[str, object]]:
    bars = [build_bar(day_index, 100.0, volume=1_000_000.0) for day_index in range(5)]
    bars.append(
        build_bar(
            5,
            105.0,
            open_price=101.0,
            volume=3_000_000.0,
            amount=315_000_000.0,
        )
    )
    bars.append(build_bar(6, 108.0, volume=1_000_000.0))
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


def test_strategy_evaluation_api_returns_research_metrics(monkeypatch):
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
            "items": build_volume_price_breakout_evaluation_bars(),
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
            "/strategies/evaluate",
            params={
                "symbol": "aapl",
                "start": "2026-01-01",
                "end": "2026-01-31",
                "strategies": "volume_price_breakout",
                "forward_windows": "1",
                "benchmark_symbol": "spy",
                "provider": "mock",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["status"] == "ok"
    assert payload["research_signal_only"] is True
    assert payload["source"] == "mock"
    assert payload["effective_provider"] == "mock"
    assert payload["benchmark_symbol"] == "SPY"
    assert payload["metrics"]["volume_price_breakout"]["windows"]["1"]["sample_size"] == 1
    assert [call["symbol"] for call in service_calls] == ["AAPL", "SPY"]
    assert all(call["provider_name"] == "mock" for call in service_calls)


def test_strategy_evaluation_api_rejects_invalid_forward_windows_before_provider(monkeypatch):
    service_calls: list[dict[str, object]] = []

    def fake_get_bars_payload(*args, **kwargs):
        service_calls.append({"called": True})
        return {"items": []}

    monkeypatch.setattr(
        strategy_screening_router.market_data_service,
        "get_bars_payload",
        fake_get_bars_payload,
    )

    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get(
            "/strategies/evaluate",
            params={
                "symbol": "AAPL",
                "start": "2026-01-01",
                "end": "2026-01-31",
                "forward_windows": "1,bad",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "forward_windows must be comma-separated integers"
    assert service_calls == []


def test_strategy_evaluation_api_maps_provider_failure_to_http_502(monkeypatch):
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
        response = client.get(
            "/strategies/evaluate",
            params={"symbol": "AAPL", "start": "2026-01-01", "end": "2026-01-31"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == {
        "message": "Market data provider unavailable for strategy evaluation.",
        "provider": "mock",
        "category": "unavailable",
    }
