from fastapi import APIRouter
from pydantic import BaseModel, Field

from packages.services.platform_settings import get_platform_settings_public, update_platform_settings

router = APIRouter(prefix="/settings", tags=["settings"])


class PlatformSettingsUpdate(BaseModel):
    market_data_provider: str | None = None
    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_api_base: str | None = None
    akshare_enabled: bool | None = None
    tushare_token: str | None = None
    tushare_http_url: str | None = None
    color_scheme: str | None = None
    favorite_macro_indicator_codes: list[str] | str | None = None


@router.get("/platform")
def read_platform_settings() -> dict[str, object]:
    return {"source": "platform_settings", **get_platform_settings_public()}


@router.put("/platform")
def write_platform_settings(body: PlatformSettingsUpdate) -> dict[str, object]:
    updates = body.model_dump(exclude_unset=True)
    return {"source": "platform_settings", **update_platform_settings(updates)}
