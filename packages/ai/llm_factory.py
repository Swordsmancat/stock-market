from collections.abc import Mapping

from packages.ai.provider import LLMProvider, MockLLMProvider, OpenAICompatibleLLMProvider
from packages.services.platform_settings import (
    get_platform_settings,
    has_invalid_explicit_llm_api_base,
    normalize_llm_api_base,
)
from packages.shared.config import DEFAULT_LLM_MODEL


def get_llm_provider(platform_settings: Mapping[str, object] | None = None) -> LLMProvider:
    settings = platform_settings if platform_settings is not None else get_platform_settings()
    provider_name = str(settings.get("llm_provider", "mock")).strip().lower()
    if provider_name == "openai":
        raw_api_base = settings.get("llm_api_base", "")
        if has_invalid_explicit_llm_api_base(raw_api_base):
            return MockLLMProvider()
        return OpenAICompatibleLLMProvider(
            api_key=str(settings.get("llm_api_key", "") or ""),
            api_base=normalize_llm_api_base(raw_api_base),
            model=str(settings.get("llm_model", DEFAULT_LLM_MODEL) or DEFAULT_LLM_MODEL),
        )
    return MockLLMProvider()
