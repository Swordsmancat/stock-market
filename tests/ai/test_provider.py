import pytest

from packages.ai import llm_factory
from packages.ai.provider import MockLLMProvider, OpenAICompatibleLLMProvider
from packages.shared.config import DEFAULT_LLM_MODEL


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {
            "choices": [
                {
                    "message": {
                        "content": "generated answer",
                    }
                }
            ]
        }


def test_openai_compatible_provider_sends_configured_model(monkeypatch):
    request: dict[str, object] = {}

    def fake_post(url: str, **kwargs: object) -> FakeResponse:
        request["url"] = url
        request.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("packages.ai.provider.httpx.post", fake_post)
    provider = OpenAICompatibleLLMProvider(
        api_key=" secret-key ",
        api_base=" https://api.deepseek.com/v1/ ",
        model=" deepseek-chat ",
    )

    assert provider.generate("Explain the shortlist") == "generated answer"
    assert request["url"] == "https://api.deepseek.com/v1/chat/completions"
    assert request["headers"] == {
        "Authorization": "Bearer secret-key",
        "Content-Type": "application/json",
    }
    assert request["json"] == {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "Explain the shortlist"}],
        "temperature": 0.2,
    }
    assert request["timeout"] == 60.0


def test_openai_compatible_provider_rejects_missing_key(monkeypatch):
    def unexpected_post(*args: object, **kwargs: object) -> None:
        raise AssertionError("HTTP request should not be made")

    monkeypatch.setattr("packages.ai.provider.httpx.post", unexpected_post)
    provider = OpenAICompatibleLLMProvider(api_key="   ")

    with pytest.raises(ValueError, match="LLM API key is not configured"):
        provider.generate("prompt")


def test_llm_factory_passes_configured_model(monkeypatch):
    def unexpected_settings_read():
        raise AssertionError("The explicit settings snapshot must be reused")

    monkeypatch.setattr(
        llm_factory,
        "get_platform_settings",
        unexpected_settings_read,
    )

    provider = llm_factory.get_llm_provider(
        {
            "llm_provider": "openai",
            "llm_api_key": "secret",
            "llm_api_base": "https://api.deepseek.com/v1",
            "llm_model": "deepseek-chat",
        }
    )

    assert isinstance(provider, OpenAICompatibleLLMProvider)
    assert provider.api_base == "https://api.deepseek.com/v1"
    assert provider.model == "deepseek-chat"


def test_llm_factory_uses_legacy_default_model(monkeypatch):
    monkeypatch.setattr(
        llm_factory,
        "get_platform_settings",
        lambda: {
            "llm_provider": "openai",
            "llm_api_key": "secret",
            "llm_api_base": "https://api.openai.com/v1",
        },
    )

    provider = llm_factory.get_llm_provider()

    assert isinstance(provider, OpenAICompatibleLLMProvider)
    assert provider.model == DEFAULT_LLM_MODEL


@pytest.mark.parametrize(
    "invalid_api_base",
    ["https://user:password@llm.example.test/v1", False, 0, [], {}],
)
def test_llm_factory_disables_external_provider_for_invalid_explicit_base(
    monkeypatch,
    invalid_api_base,
):
    def unexpected_provider(*args: object, **kwargs: object) -> None:
        raise AssertionError("External provider must not be constructed")

    monkeypatch.setattr(llm_factory, "OpenAICompatibleLLMProvider", unexpected_provider)

    provider = llm_factory.get_llm_provider(
        {
            "llm_provider": "openai",
            "llm_api_key": "custom-service-secret",
            "llm_api_base": invalid_api_base,
            "llm_model": "custom-model",
        }
    )

    assert isinstance(provider, MockLLMProvider)
