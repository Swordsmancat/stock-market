from fastapi.testclient import TestClient

from apps.api.main import app


def test_platform_settings_round_trip(tmp_path, monkeypatch):
    settings_file = tmp_path / "platform_settings.json"
    monkeypatch.setattr(
        "packages.services.platform_settings.SETTINGS_PATH",
        settings_file,
    )

    client = TestClient(app)
    initial = client.get("/settings/platform")
    assert initial.status_code == 200
    assert initial.json()["market_data_provider"] == "yfinance"

    updated = client.put(
        "/settings/platform",
        json={
            "market_data_provider": "mock",
            "llm_provider": "openai",
            "llm_api_base": "https://example.com/v1",
        },
    )
    assert updated.status_code == 200
    payload = updated.json()
    assert payload["market_data_provider"] == "mock"
    assert payload["llm_provider"] == "openai"
    assert payload["llm_api_base"] == "https://example.com/v1"
