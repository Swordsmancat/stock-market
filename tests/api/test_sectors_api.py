from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers import sectors as sectors_router


def test_hot_sectors_static_fixture_is_labelled_as_degraded_mock_data():
    client = TestClient(app)

    response = client.get("/sectors/hot", params={"limit": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["data_mode"] == "mock"
    assert payload["source"] == "static_sector_fixture"
    assert payload["provider"] == "static_fixture"
    assert payload["sector_type"] == "industry"
    assert payload["window"] == "today"
    assert payload["availability"]["status"] == "mock"
    assert payload["flow_definition"]["metric"] == "static_fixture_demo_value"
    assert payload["provider_capabilities"]["sector_ranking"]["status"] == "mock"
    assert payload["count"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["top_constituents"]
    assert payload["items"][0]["breadth"]["status"] == "mock"
    assert payload["items"][0]["history"]["status"] == "unavailable"


def test_hot_sectors_passes_provider_to_service(monkeypatch):
    captured_arguments = {}

    def get_hot_sectors_payload_stub(
        limit: int,
        provider_name: str | None = None,
        sector_type: str | None = None,
        window: str | None = None,
    ) -> dict[str, object]:
        captured_arguments["limit"] = limit
        captured_arguments["provider_name"] = provider_name
        captured_arguments["sector_type"] = sector_type
        captured_arguments["window"] = window
        return {
            "status": "ok",
            "data_mode": "live",
            "source": "fake_provider_sector_flow",
            "provider": "fake_provider",
            "requested_provider": provider_name,
            "effective_provider": "fake_provider",
            "as_of": "2026-07-04T09:30:00+00:00",
            "generated_at": "2026-07-04T09:31:00+00:00",
            "is_realtime": True,
            "is_delayed": False,
            "delay_minutes": None,
            "market": "CN",
            "sector_type": sector_type,
            "window": window,
            "taxonomy_version": "sector-taxonomy-v1",
            "flow_definition": {"metric": "provider_reported_net_inflow"},
            "availability": {"status": "available"},
            "message": "Verified provider data.",
            "count": 0,
            "items": [],
        }

    monkeypatch.setattr(sectors_router, "get_hot_sectors_payload", get_hot_sectors_payload_stub)
    client = TestClient(app)

    response = client.get(
        "/sectors/hot",
        params={
            "limit": 2,
            "provider": "fake_provider",
            "sector_type": "concept",
            "window": "5d",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert captured_arguments == {
        "limit": 2,
        "provider_name": "fake_provider",
        "sector_type": "concept",
        "window": "5d",
    }
    assert payload["status"] == "ok"
    assert payload["data_mode"] == "live"
    assert payload["provider"] == "fake_provider"
    assert payload["sector_type"] == "concept"
    assert payload["window"] == "5d"


def test_hot_sectors_unknown_provider_returns_unavailable_payload():
    client = TestClient(app)

    response = client.get("/sectors/hot", params={"provider": "unknown_provider"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "unavailable"
    assert payload["data_mode"] == "none"
    assert payload["requested_provider"] == "unknown_provider"
    assert payload["availability"]["breadth"] == "unavailable"
    assert payload["provider_capabilities"]["sector_fund_flow"]["status"] == "unavailable"
    assert payload["count"] == 0
    assert payload["items"] == []


def test_hot_sectors_unknown_sector_type_returns_unavailable_payload():
    client = TestClient(app)

    response = client.get("/sectors/hot", params={"sector_type": "region"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "unavailable"
    assert payload["sector_type"] == "region"


def test_hot_sectors_limit_validation_is_preserved():
    client = TestClient(app)

    response = client.get("/sectors/hot", params={"limit": 11})

    assert response.status_code == 422
