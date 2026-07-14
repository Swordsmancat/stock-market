import json

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
import packages.services.platform_settings as platform_settings_service
from packages.shared.config import DEFAULT_LLM_API_BASE, DEFAULT_LLM_MODEL


def test_normalize_llm_model_uses_legacy_default():
    assert platform_settings_service.normalize_llm_model(None) == DEFAULT_LLM_MODEL
    assert platform_settings_service.normalize_llm_model(False) == DEFAULT_LLM_MODEL
    assert platform_settings_service.normalize_llm_model({}) == DEFAULT_LLM_MODEL
    assert platform_settings_service.normalize_llm_model("   ") == DEFAULT_LLM_MODEL
    assert platform_settings_service.normalize_llm_model("  deepseek-chat  ") == "deepseek-chat"


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
    assert initial.json()["llm_model"] == DEFAULT_LLM_MODEL
    assert initial.json()["news_search_enabled_providers"] == ["anspire", "serpapi_baidu"]
    assert initial.json()["news_search_provider_keys"] == {}
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
            "news_search_provider_order": ["serpapi_baidu", "anspire"],
            "news_search_enabled_providers": ["serpapi_baidu"],
            "news_search_provider_keys": {
                "anspire": "anspire-secret",
                "serpapi_baidu": "serpapi-secret",
            },
            "news_search_max_results": 12,
            "news_search_timeout_seconds": 6,
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
    assert payload["llm_model"] == DEFAULT_LLM_MODEL
    assert payload["news_search_provider_order"][:2] == ["serpapi_baidu", "anspire"]
    assert payload["news_search_enabled_providers"] == ["serpapi_baidu"]
    assert payload["news_search_provider_keys"] == {}
    assert payload["news_search_provider_keys_configured"] == {
        "anspire": True,
        "serpapi_baidu": True,
    }
    assert payload["news_search_max_results"] == 12
    assert payload["news_search_timeout_seconds"] == 6.0
    assert "anspire-secret" not in str(payload)
    assert "serpapi-secret" not in str(payload)
    assert payload["favorite_macro_indicator_codes"] == [
        "buffett_indicator_cn",
        "us_10y_yield",
    ]


def test_platform_settings_llm_config_is_normalized_redacted_and_preserved(
    tmp_path,
    monkeypatch,
):
    settings_file = tmp_path / "platform_settings.json"
    settings_file.write_text(
        json.dumps(
            {
                "llm_provider": "openai",
                "llm_api_key": "legacy-secret",
                "llm_api_base": "https://user:base-secret@llm.example.com/v1",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "packages.services.platform_settings.SETTINGS_PATH",
        settings_file,
    )
    monkeypatch.setitem(platform_settings_service.DEFAULTS, "llm_model", DEFAULT_LLM_MODEL)

    client = TestClient(app)
    legacy = client.get("/settings/platform")
    assert legacy.status_code == 200
    assert legacy.json()["llm_model"] == DEFAULT_LLM_MODEL
    assert legacy.json()["llm_api_base"] == DEFAULT_LLM_API_BASE
    assert legacy.json()["llm_provider"] == "mock"
    assert legacy.json()["llm_api_key"] == ""
    assert legacy.json()["llm_api_key_configured"] is False
    assert "legacy-secret" not in str(legacy.json())

    updated = client.put(
        "/settings/platform",
        json={
            "llm_api_key": "deepseek-secret",
            "llm_api_base": "  https://api.deepseek.com/v1/  ",
            "llm_model": "  deepseek-chat  ",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["llm_api_base"] == "https://api.deepseek.com/v1"
    assert updated.json()["llm_model"] == "deepseek-chat"
    assert updated.json()["llm_api_key"] == ""
    assert updated.json()["llm_api_key_configured"] is True
    assert "deepseek-secret" not in str(updated.json())

    preserved = client.put(
        "/settings/platform",
        json={"llm_api_key": "   "},
    )
    assert preserved.status_code == 200
    stored = json.loads(settings_file.read_text(encoding="utf-8"))
    assert stored["llm_api_key"] == "deepseek-secret"
    assert stored["llm_api_base"] == "https://api.deepseek.com/v1"
    assert stored["llm_model"] == "deepseek-chat"

    switched_without_key = client.put(
        "/settings/platform",
        json={
            "llm_provider": "openai",
            "llm_api_key": " ",
            "llm_api_base": "https://api.openai.com/v1",
            "llm_model": DEFAULT_LLM_MODEL,
        },
    )
    assert switched_without_key.status_code == 200
    assert switched_without_key.json()["llm_api_key_configured"] is False
    assert json.loads(settings_file.read_text(encoding="utf-8"))["llm_api_key"] == ""


@pytest.mark.parametrize("invalid_stored_base", [False, 0, [], {}])
def test_platform_settings_fails_closed_for_non_string_stored_base(
    tmp_path,
    monkeypatch,
    invalid_stored_base,
):
    settings_file = tmp_path / "platform_settings.json"
    settings_file.write_text(
        json.dumps(
            {
                "llm_provider": "openai",
                "llm_api_key": "custom-service-secret",
                "llm_api_base": invalid_stored_base,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "packages.services.platform_settings.SETTINGS_PATH",
        settings_file,
    )

    payload = TestClient(app).get("/settings/platform").json()

    assert payload["llm_provider"] == "mock"
    assert payload["llm_api_base"] == DEFAULT_LLM_API_BASE
    assert payload["llm_api_key"] == ""
    assert payload["llm_api_key_configured"] is False
    assert "custom-service-secret" not in str(payload)


def test_platform_settings_uses_configured_defaults_for_blank_legacy_llm_fields(
    tmp_path,
    monkeypatch,
):
    settings_file = tmp_path / "platform_settings.json"
    settings_file.write_text(
        json.dumps(
            {
                "llm_provider": "openai",
                "llm_api_key": "stored-secret",
                "llm_api_base": " ",
                "llm_model": " ",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "packages.services.platform_settings.SETTINGS_PATH",
        settings_file,
    )
    monkeypatch.setitem(
        platform_settings_service.DEFAULTS,
        "llm_api_base",
        "https://env-llm.example.test/v1",
    )
    monkeypatch.setitem(platform_settings_service.DEFAULTS, "llm_model", "env-model")

    payload = TestClient(app).get("/settings/platform").json()

    assert payload["llm_provider"] == "openai"
    assert payload["llm_api_base"] == "https://env-llm.example.test/v1"
    assert payload["llm_model"] == "env-model"
    assert payload["llm_api_key_configured"] is True


@pytest.mark.parametrize(
    "invalid_update",
    [
        {"llm_provider": "deepseek"},
        {"llm_model": "   "},
        {"llm_model": "x" * 129},
        {"llm_api_base": "ftp://llm.example.com/v1"},
        {"llm_api_base": "/v1/chat/completions"},
        {"llm_api_base": "https://user:secret@llm.example.com/v1"},
        {"llm_api_base": "https://llm.example.com/v1?api_key=secret"},
        {"llm_api_base": "https://llm.example.com:bad/v1"},
        {"llm_api_base": "https://llm.example.com/v1?"},
        {"llm_api_base": "https://exa mple.com/v1"},
        {"llm_api_base": "https:\\example.com\\v1"},
        {"llm_api_base": "https://%zz/v1"},
        {"llm_api_base": "https://%2F/v1"},
        {"llm_api_base": "https:example.com/v1"},
        {"llm_api_base": "http:///example.com/v1"},
        {"llm_api_base": "https://exa^mple.com/v1"},
        {"llm_api_base": "https://exa|mple.com/v1"},
        {"llm_api_base": "https://[v1.fe80::]/v1"},
    ],
)
def test_platform_settings_rejects_invalid_llm_config_without_writing(
    tmp_path,
    monkeypatch,
    invalid_update,
):
    settings_file = tmp_path / "platform_settings.json"
    monkeypatch.setattr(
        "packages.services.platform_settings.SETTINGS_PATH",
        settings_file,
    )

    response = TestClient(app).put("/settings/platform", json=invalid_update)

    assert response.status_code == 422
    assert not settings_file.exists()
    assert "secret" not in response.text


def test_platform_settings_validation_errors_do_not_echo_invalid_key(tmp_path, monkeypatch):
    settings_file = tmp_path / "platform_settings.json"
    monkeypatch.setattr(
        "packages.services.platform_settings.SETTINGS_PATH",
        settings_file,
    )

    response = TestClient(app).put(
        "/settings/platform",
        json={"llm_api_key": {"value": "fake-secret"}},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "invalid_key",
                "loc": ["body", "llm_api_key"],
                "msg": "Invalid value for llm_api_key.",
            }
        ]
    }
    assert "fake-secret" not in response.text
    assert not settings_file.exists()


def test_platform_settings_validation_errors_do_not_echo_nested_keys(tmp_path, monkeypatch):
    settings_file = tmp_path / "platform_settings.json"
    monkeypatch.setattr(
        "packages.services.platform_settings.SETTINGS_PATH",
        settings_file,
    )

    response = TestClient(app).put(
        "/settings/platform",
        json={"news_search_provider_keys": {"fake-secret-key": {"nested": "value"}}},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "news_search_provider_keys"]
    assert "fake-secret-key" not in response.text
    assert not settings_file.exists()


def test_platform_settings_accepts_normalized_llm_config_and_legacy_omission(
    tmp_path,
    monkeypatch,
):
    settings_file = tmp_path / "platform_settings.json"
    monkeypatch.setattr(
        "packages.services.platform_settings.SETTINGS_PATH",
        settings_file,
    )

    response = TestClient(app).put(
        "/settings/platform",
        json={
            "llm_provider": " OPENAI ",
            "llm_api_base": " http://localhost:11434/v1/ ",
            "llm_model": " local-model ",
        },
    )

    assert response.status_code == 200
    assert response.json()["llm_provider"] == "openai"
    assert response.json()["llm_api_base"] == "http://localhost:11434/v1"
    assert response.json()["llm_model"] == "local-model"

    legacy = TestClient(app).put(
        "/settings/platform",
        json={"market_data_provider": "mock"},
    )
    assert legacy.status_code == 200
    assert legacy.json()["llm_model"] == "local-model"


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


def test_platform_settings_preserves_blank_news_provider_keys(tmp_path, monkeypatch):
    settings_file = tmp_path / "platform_settings.json"
    monkeypatch.setattr(
        "packages.services.platform_settings.SETTINGS_PATH",
        settings_file,
    )

    client = TestClient(app)
    first = client.put(
        "/settings/platform",
        json={
            "news_search_provider_keys": {
                "anspire": "first-anspire-key",
                "serpapi_baidu": "first-serpapi-key",
            },
        },
    )
    second = client.put(
        "/settings/platform",
        json={
            "news_search_provider_keys": {
                "anspire": "",
                "serpapi_baidu": "updated-serpapi-key",
            },
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["news_search_provider_keys_configured"] == {
        "anspire": True,
        "serpapi_baidu": True,
    }
    raw_file = settings_file.read_text(encoding="utf-8")
    assert "first-anspire-key" in raw_file
    assert "updated-serpapi-key" in raw_file


def test_llm_connection_endpoint_returns_only_safe_connection_metadata(monkeypatch):
    calls = 0

    class FakeLLM:
        def generate(self, prompt: str) -> str:
            nonlocal calls
            calls += 1
            return "private answer that is intentionally discarded"

    settings = {
        "llm_provider": "openai",
        "llm_api_key": "private-api-key",
        "llm_api_base": "https://api.deepseek.com/v1",
        "llm_model": "deepseek-chat",
    }
    monotonic_values = iter((50.0, 50.2))
    monkeypatch.setattr(
        "packages.services.llm_connection.get_platform_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "packages.services.llm_connection.get_llm_provider",
        lambda _settings: FakeLLM(),
    )
    monkeypatch.setattr(
        "packages.services.llm_connection.monotonic",
        lambda: next(monotonic_values),
    )

    response = TestClient(app).post("/settings/llm/test")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "code": "connected",
        "provider": "openai",
        "model": "deepseek-chat",
        "latency_ms": 200,
    }
    assert calls == 1
    assert "private-api-key" not in response.text
    assert "private answer" not in response.text
    assert "Reply with exactly OK" not in response.text


@pytest.mark.parametrize(
    ("settings", "expected_status", "expected_code"),
    [
        pytest.param(
            {
                "llm_provider": "mock",
                "llm_api_key": "",
                "llm_api_base": DEFAULT_LLM_API_BASE,
                "llm_model": DEFAULT_LLM_MODEL,
            },
            400,
            "provider_disabled",
            id="disabled",
        ),
        pytest.param(
            {
                "llm_provider": "openai",
                "llm_api_key": "",
                "llm_api_base": DEFAULT_LLM_API_BASE,
                "llm_model": DEFAULT_LLM_MODEL,
            },
            400,
            "key_not_configured",
            id="missing-key",
        ),
        pytest.param(
            {
                "llm_provider": "openai",
                "llm_api_key": "private-api-key",
                "llm_api_base": "https://user:password@example.test/v1",
                "llm_model": DEFAULT_LLM_MODEL,
            },
            400,
            "invalid_configuration",
            id="invalid-configuration",
        ),
    ],
)
def test_llm_connection_endpoint_maps_precondition_errors(
    monkeypatch,
    settings,
    expected_status,
    expected_code,
):
    monkeypatch.setattr(
        "packages.services.llm_connection.get_platform_settings",
        lambda: settings,
    )

    response = TestClient(app).post("/settings/llm/test")

    assert response.status_code == expected_status
    assert response.json()["status"] == "error"
    assert response.json()["code"] == expected_code
    assert "private-api-key" not in response.text
    assert "user:password" not in response.text


def test_llm_connection_endpoint_sanitizes_provider_errors(monkeypatch):
    calls = 0

    class FailingLLM:
        def generate(self, prompt: str) -> str:
            nonlocal calls
            calls += 1
            raise RuntimeError(
                "private-api-key Authorization: Bearer private-api-key "
                f"upstream-body prompt={prompt}"
            )

    settings = {
        "llm_provider": "openai",
        "llm_api_key": "private-api-key",
        "llm_api_base": "https://api.deepseek.com/v1",
        "llm_model": "deepseek-chat",
    }
    monotonic_values = iter((10.0, 10.5))
    monkeypatch.setattr(
        "packages.services.llm_connection.get_platform_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "packages.services.llm_connection.get_llm_provider",
        lambda _settings: FailingLLM(),
    )
    monkeypatch.setattr(
        "packages.services.llm_connection.monotonic",
        lambda: next(monotonic_values),
    )

    response = TestClient(app).post("/settings/llm/test")

    assert response.status_code == 502
    assert response.json() == {
        "status": "error",
        "code": "provider_unavailable",
        "provider": "openai",
        "model": "deepseek-chat",
        "latency_ms": 500,
        "message": "LLM provider is unavailable.",
    }
    assert calls == 1
    for secret in (
        "private-api-key",
        "Authorization",
        "Bearer",
        "upstream-body",
        "Reply with exactly OK",
    ):
        assert secret not in response.text
