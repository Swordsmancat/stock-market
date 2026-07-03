from fastapi.testclient import TestClient

from apps.api.main import app


def test_hot_sectors_static_fixture_is_labelled_as_degraded_mock_data():
    client = TestClient(app)

    response = client.get("/sectors/hot", params={"limit": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["data_mode"] == "mock"
    assert payload["source"] == "static_sector_fixture"
    assert payload["count"] == 1
    assert len(payload["items"]) == 1
