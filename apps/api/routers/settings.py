from fastapi import APIRouter, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field, field_validator
from urllib.parse import urlsplit
from starlette.responses import JSONResponse

from packages.services.llm_connection import (
    LLMConnectionTestError,
    run_llm_connection_test,
)
from packages.services.platform_settings import (
    get_platform_settings_public,
    is_valid_llm_api_base,
    update_platform_settings,
)

class SecretSafeSettingsRoute(APIRoute):
    def get_route_handler(self):
        route_handler = super().get_route_handler()

        async def secret_safe_route_handler(request: Request):
            try:
                return await route_handler(request)
            except RequestValidationError as error:
                errors = error.errors()
                location = errors[0].get("loc", ()) if errors else ()
                allowed_fields = {
                    "market_data_provider",
                    "llm_provider",
                    "llm_api_key",
                    "llm_api_base",
                    "llm_model",
                    "akshare_enabled",
                    "tushare_token",
                    "tushare_http_url",
                    "eastmoney_proxy_url",
                    "eastmoney_cookie",
                    "color_scheme",
                    "favorite_macro_indicator_codes",
                    "news_search_provider_order",
                    "news_search_enabled_providers",
                    "news_search_provider_keys",
                    "news_search_max_results",
                    "news_search_timeout_seconds",
                }
                candidate_field = next(iter(location[1:]), None)
                field = candidate_field if candidate_field in allowed_fields else "body"
                code = {
                    "llm_provider": "invalid_provider",
                    "llm_api_key": "invalid_key",
                    "llm_api_base": "invalid_base",
                    "llm_model": "invalid_model",
                }.get(field, "invalid_setting")
                detail = (
                    f"Invalid value for {field}."
                    if field != "body"
                    else "Invalid platform settings payload."
                )
                return JSONResponse(
                    status_code=422,
                    content={
                        "detail": [
                            {
                                "type": code,
                                "loc": ["body", field] if field != "body" else ["body"],
                                "msg": detail,
                            }
                        ]
                    },
                )

        return secret_safe_route_handler


router = APIRouter(
    prefix="/settings",
    tags=["settings"],
    route_class=SecretSafeSettingsRoute,
)


class PlatformSettingsUpdate(BaseModel):
    market_data_provider: str | None = None
    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_api_base: str | None = None
    llm_model: str | None = None
    akshare_enabled: bool | None = None
    tushare_token: str | None = None
    tushare_http_url: str | None = None
    eastmoney_proxy_url: str | None = None
    eastmoney_cookie: str | None = None
    color_scheme: str | None = None
    favorite_macro_indicator_codes: list[str] | str | None = None
    news_search_provider_order: list[str] | str | None = None
    news_search_enabled_providers: list[str] | str | None = None
    news_search_provider_keys: dict[str, str] | None = None
    news_search_max_results: int | None = Field(default=None, ge=1, le=20)
    news_search_timeout_seconds: float | None = Field(default=None, ge=1, le=30)

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in {"mock", "openai"}:
            raise ValueError("llm_provider must be 'mock' or 'openai'")
        return normalized

    @field_validator("llm_model")
    @classmethod
    def validate_llm_model(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("llm_model must not be blank")
        if len(normalized) > 128:
            raise ValueError("llm_model must be at most 128 characters")
        return normalized

    @field_validator("llm_api_base")
    @classmethod
    def validate_llm_api_base(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().rstrip("/")
        if not is_valid_llm_api_base(normalized):
            raise ValueError(
                "llm_api_base must be an absolute HTTP(S) URL without credentials, query, or fragment"
            )
        return normalized

    @field_validator("eastmoney_proxy_url")
    @classmethod
    def validate_eastmoney_proxy_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return value
        normalized = value.strip()
        parsed = urlsplit(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.query or parsed.fragment:
            raise ValueError("eastmoney_proxy_url must be an absolute HTTP(S) proxy URL")
        return normalized


@router.get("/platform")
def read_platform_settings() -> dict[str, object]:
    return {"source": "platform_settings", **get_platform_settings_public()}


@router.put("/platform")
def write_platform_settings(body: PlatformSettingsUpdate) -> dict[str, object]:
    updates = body.model_dump(exclude_unset=True)
    return {"source": "platform_settings", **update_platform_settings(updates)}


@router.post("/llm/test")
def test_llm_connection() -> JSONResponse:
    try:
        payload = run_llm_connection_test()
    except LLMConnectionTestError as error:
        return JSONResponse(
            status_code=error.http_status_code,
            content=error.to_payload(),
        )
    return JSONResponse(status_code=200, content=payload)
