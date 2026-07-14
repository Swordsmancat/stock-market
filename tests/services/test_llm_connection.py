import json
from pathlib import Path

import pytest

from packages.services import llm_connection


def _configured_settings(**overrides: object) -> dict[str, object]:
    settings: dict[str, object] = {
        "llm_provider": "openai",
        "llm_api_key": "private-api-key",
        "llm_api_base": "https://api.deepseek.com/v1",
        "llm_model": "deepseek-chat",
    }
    settings.update(overrides)
    return settings


def test_llm_connection_calls_provider_once_discards_answer_and_does_not_write(
    monkeypatch,
):
    settings = _configured_settings()
    original_settings = dict(settings)
    prompts: list[str] = []
    writes: list[str] = []

    class FakeLLM:
        def generate(self, prompt: str) -> str:
            prompts.append(prompt)
            return "private generated answer that must be discarded"

    def fake_provider(settings_snapshot):
        assert settings_snapshot is settings
        return FakeLLM()

    def track_write(path: Path, *args: object, **kwargs: object) -> int:
        writes.append(str(path))
        return 0

    monotonic_values = iter((100.0, 100.1239))
    monkeypatch.setattr(llm_connection, "get_platform_settings", lambda: settings)
    monkeypatch.setattr(llm_connection, "get_llm_provider", fake_provider)
    monkeypatch.setattr(llm_connection, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(Path, "write_text", track_write)

    payload = llm_connection.run_llm_connection_test()

    assert payload == {
        "status": "ok",
        "code": "connected",
        "provider": "openai",
        "model": "deepseek-chat",
        "latency_ms": 123,
    }
    assert prompts == [llm_connection.LLM_CONNECTION_TEST_PROMPT]
    assert settings == original_settings
    assert writes == []
    serialized = json.dumps(payload)
    assert "private-api-key" not in serialized
    assert "private generated answer" not in serialized
    assert llm_connection.LLM_CONNECTION_TEST_PROMPT not in serialized


@pytest.mark.parametrize(
    ("settings", "expected_code"),
    [
        pytest.param(
            _configured_settings(llm_provider="mock"),
            "provider_disabled",
            id="disabled",
        ),
        pytest.param(
            _configured_settings(llm_api_key="  "),
            "key_not_configured",
            id="missing-key",
        ),
        pytest.param(
            _configured_settings(llm_api_base="https://user:secret@example.test/v1"),
            "invalid_configuration",
            id="invalid-base",
        ),
        pytest.param(
            _configured_settings(llm_model="  "),
            "invalid_configuration",
            id="invalid-model",
        ),
        pytest.param(
            _configured_settings(llm_provider="unknown"),
            "invalid_configuration",
            id="invalid-provider",
        ),
    ],
)
def test_llm_connection_rejects_invalid_settings_without_provider_call(
    monkeypatch,
    settings,
    expected_code,
):
    provider_calls = 0

    def unexpected_provider(settings_snapshot):
        nonlocal provider_calls
        provider_calls += 1
        raise AssertionError("Provider must not be constructed")

    monkeypatch.setattr(llm_connection, "get_platform_settings", lambda: settings)
    monkeypatch.setattr(llm_connection, "get_llm_provider", unexpected_provider)

    with pytest.raises(llm_connection.LLMConnectionTestError) as caught:
        llm_connection.run_llm_connection_test()

    error = caught.value
    assert error.http_status_code == 400
    assert error.code == expected_code
    assert provider_calls == 0
    assert set(error.to_payload()) <= {"status", "code", "provider", "model", "message"}
    serialized = json.dumps(error.to_payload())
    assert "private-api-key" not in serialized
    assert "user:secret" not in serialized


def test_llm_connection_sanitizes_provider_failure_and_calls_once(monkeypatch):
    settings = _configured_settings()
    calls = 0

    class FailingLLM:
        def generate(self, prompt: str) -> str:
            nonlocal calls
            calls += 1
            raise RuntimeError(
                "private-api-key Authorization: Bearer private-api-key "
                "https://user:password@example.test/v1 upstream-body stack-trace "
                f"prompt={prompt}"
            )

    monotonic_values = iter((20.0, 20.25))
    monkeypatch.setattr(llm_connection, "get_platform_settings", lambda: settings)
    monkeypatch.setattr(llm_connection, "get_llm_provider", lambda _settings: FailingLLM())
    monkeypatch.setattr(llm_connection, "monotonic", lambda: next(monotonic_values))

    with pytest.raises(llm_connection.LLMConnectionTestError) as caught:
        llm_connection.run_llm_connection_test()

    assert calls == 1
    assert caught.value.http_status_code == 502
    assert caught.value.to_payload() == {
        "status": "error",
        "code": "provider_unavailable",
        "provider": "openai",
        "model": "deepseek-chat",
        "latency_ms": 250,
        "message": "LLM provider is unavailable.",
    }
    serialized = json.dumps(caught.value.to_payload())
    for secret in (
        "private-api-key",
        "Authorization",
        "Bearer",
        "upstream-body",
        "stack-trace",
        "Reply with exactly OK",
        "user:password",
    ):
        assert secret not in serialized


@pytest.mark.parametrize("answer", [None, "", "  ", {}, []])
def test_llm_connection_rejects_empty_or_malformed_generation(monkeypatch, answer):
    settings = _configured_settings()
    calls = 0

    class FakeLLM:
        def generate(self, prompt: str):
            nonlocal calls
            calls += 1
            return answer

    monotonic_values = iter((7.0, 7.01))
    monkeypatch.setattr(llm_connection, "get_platform_settings", lambda: settings)
    monkeypatch.setattr(llm_connection, "get_llm_provider", lambda _settings: FakeLLM())
    monkeypatch.setattr(llm_connection, "monotonic", lambda: next(monotonic_values))

    with pytest.raises(llm_connection.LLMConnectionTestError) as caught:
        llm_connection.run_llm_connection_test()

    assert calls == 1
    assert caught.value.http_status_code == 502
    assert caught.value.code == "invalid_provider_response"
    assert set(caught.value.to_payload()) == {
        "status",
        "code",
        "provider",
        "model",
        "latency_ms",
        "message",
    }
