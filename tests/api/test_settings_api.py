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
    assert initial.json()["favorite_macro_indicator_codes"][:2] == [
        "buffett_indicator_us",
        "buffett_indicator_cn",
    ]

    updated = client.put(
        "/settings/platform",
        json={
            "market_data_provider": "mock",
            "llm_provider": "openai",
            "llm_api_base": "https://example.com/v1",
            "favorite_macro_indicator_codes": [
                " buffett_indicator_cn ",
                "us_10y_yield",
                "",
                "buffett_indicator_cn",
            ],
        },
    )
    assert updated.status_code == 200
    payload = updated.json()
    assert payload["market_data_provider"] == "mock"
    assert payload["llm_provider"] == "openai"
    assert payload["llm_api_base"] == "https://example.com/v1"
    assert payload["favorite_macro_indicator_codes"] == [
        "buffett_indicator_cn",
        "us_10y_yield",
    ]


def test_platform_settings_public_response_masks_tushare_token(tmp_path, monkeypatch):
    settings_file = tmp_path / "platform_settings.json"
    monkeypatch.setattr(
        "packages.services.platform_settings.SETTINGS_PATH",
        settings_file,
    )

    client = TestClient(app)
    updated = client.put(
        "/settings/platform",
        json={
            "market_data_provider": "tushare",
            "tushare_token": "secret-tushare-token",
        },
    )
    assert updated.status_code == 200

    payload = updated.json()
    assert payload["market_data_provider"] == "tushare"
    assert payload["tushare_token"] == ""
    assert payload["tushare_token_configured"] is True
    assert "secret-tushare-token" not in str(payload)

    capabilities = payload["market_data_provider_capabilities"]
    tushare_capability = next(
        capability for capability in capabilities if capability["provider"] == "tushare"
    )
    assert tushare_capability["active"] is True
    assert tushare_capability["configured"] is True
    assert tushare_capability["supports_daily_bars"] is True
    assert tushare_capability["supports_realtime_quotes"] is False
