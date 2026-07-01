from packages.ai.provider import LLMProvider, MockLLMProvider, OpenAICompatibleLLMProvider
from packages.services.platform_settings import get_platform_settings


def get_llm_provider() -> LLMProvider:
    settings = get_platform_settings()
    provider_name = settings["llm_provider"].lower()
    if provider_name == "openai":
        return OpenAICompatibleLLMProvider(
            api_key=settings["llm_api_key"],
            api_base=settings["llm_api_base"],
        )
    return MockLLMProvider()
