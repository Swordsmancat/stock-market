from __future__ import annotations

from time import monotonic

from packages.ai.llm_factory import get_llm_provider
from packages.services.platform_settings import (
    get_platform_settings,
    is_valid_llm_api_base,
)


LLM_CONNECTION_TEST_PROMPT = "Reply with exactly OK."

_ERROR_MESSAGES = {
    "provider_disabled": "LLM provider is disabled.",
    "key_not_configured": "LLM API key is not configured.",
    "invalid_configuration": "LLM configuration is invalid.",
    "provider_unavailable": "LLM provider is unavailable.",
    "invalid_provider_response": "LLM provider returned an invalid response.",
}


class LLMConnectionTestError(RuntimeError):
    def __init__(
        self,
        *,
        code: str,
        http_status_code: int,
        provider: str | None = None,
        model: str | None = None,
        latency_ms: int | None = None,
    ) -> None:
        self.code = code
        self.http_status_code = http_status_code
        self.provider = provider
        self.model = model
        self.latency_ms = latency_ms
        super().__init__(code)

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": "error",
            "code": self.code,
        }
        if self.provider is not None:
            payload["provider"] = self.provider
        if self.model is not None:
            payload["model"] = self.model
        if self.latency_ms is not None:
            payload["latency_ms"] = self.latency_ms
        payload["message"] = _ERROR_MESSAGES[self.code]
        return payload


def run_llm_connection_test() -> dict[str, object]:
    try:
        settings = get_platform_settings()
    except Exception:
        raise LLMConnectionTestError(
            code="invalid_configuration",
            http_status_code=400,
        ) from None

    provider = _normalized_provider(settings.get("llm_provider"))
    model = _safe_model(settings.get("llm_model"))
    if provider == "mock":
        raise LLMConnectionTestError(
            code="provider_disabled",
            http_status_code=400,
            provider=provider,
            model=model,
        )
    if provider != "openai":
        raise LLMConnectionTestError(
            code="invalid_configuration",
            http_status_code=400,
            model=model,
        )

    if not is_valid_llm_api_base(settings.get("llm_api_base")) or model is None:
        raise LLMConnectionTestError(
            code="invalid_configuration",
            http_status_code=400,
            provider=provider,
            model=model,
        )

    api_key = settings.get("llm_api_key")
    if not isinstance(api_key, str) or not api_key.strip():
        raise LLMConnectionTestError(
            code="key_not_configured",
            http_status_code=400,
            provider=provider,
            model=model,
        )

    started_at = monotonic()
    try:
        answer = get_llm_provider(settings).generate(LLM_CONNECTION_TEST_PROMPT)
    except Exception:
        raise LLMConnectionTestError(
            code="provider_unavailable",
            http_status_code=502,
            provider=provider,
            model=model,
            latency_ms=_elapsed_ms(started_at),
        ) from None

    latency_ms = _elapsed_ms(started_at)
    if not isinstance(answer, str) or not answer.strip():
        raise LLMConnectionTestError(
            code="invalid_provider_response",
            http_status_code=502,
            provider=provider,
            model=model,
            latency_ms=latency_ms,
        )

    return {
        "status": "ok",
        "code": "connected",
        "provider": provider,
        "model": model,
        "latency_ms": latency_ms,
    }


def _normalized_provider(value: object) -> str:
    return value.strip().lower() if isinstance(value, str) else ""


def _safe_model(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    model = value.strip()
    if not model or len(model) > 128 or not model.isprintable():
        return None
    return model


def _elapsed_ms(started_at: float) -> int:
    return max(0, int((monotonic() - started_at) * 1000))
