import json
from pathlib import Path
from typing import Any

from packages.shared.config import settings

SETTINGS_PATH = Path(__file__).resolve().parents[2] / "data" / "platform_settings.json"

DEFAULTS: dict[str, Any] = {
    "market_data_provider": settings.market_data_provider,
    "llm_provider": settings.llm_provider,
    "llm_api_key": settings.llm_api_key or "",
    "llm_api_base": "https://api.openai.com/v1",
    "akshare_enabled": False,
    "tushare_token": "",
}


def _ensure_parent() -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_platform_settings() -> dict[str, Any]:
    payload = dict(DEFAULTS)
    if SETTINGS_PATH.exists():
        try:
            stored = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(stored, dict):
                payload.update({key: stored[key] for key in DEFAULTS if key in stored})
        except json.JSONDecodeError:
            pass
    return {
        "market_data_provider": str(payload["market_data_provider"]).lower(),
        "llm_provider": str(payload["llm_provider"]).lower(),
        "llm_api_key": str(payload["llm_api_key"] or ""),
        "llm_api_base": str(payload["llm_api_base"] or DEFAULTS["llm_api_base"]),
        "akshare_enabled": bool(payload.get("akshare_enabled", False)),
        "tushare_token": str(payload.get("tushare_token", "") or ""),
    }


def get_platform_settings_public() -> dict[str, Any]:
    current = get_platform_settings()
    api_key = current["llm_api_key"]
    return {
        **current,
        "llm_api_key": api_key,
        "llm_api_key_configured": bool(api_key.strip()),
    }


def update_platform_settings(updates: dict[str, Any]) -> dict[str, Any]:
    current = get_platform_settings()
    for key in DEFAULTS:
        if key not in updates or updates[key] is None:
            continue
        if key == "llm_api_key" and not str(updates[key]).strip():
            continue
        current[key] = updates[key]
    current["market_data_provider"] = str(current["market_data_provider"]).lower()
    current["llm_provider"] = str(current["llm_provider"]).lower()
    current["akshare_enabled"] = bool(current.get("akshare_enabled", False))
    current["tushare_token"] = str(current.get("tushare_token", "") or "")
    _ensure_parent()
    SETTINGS_PATH.write_text(json.dumps(current, indent=2), encoding="utf-8")
    return get_platform_settings_public()


def get_effective_market_data_provider(requested: str | None = None) -> str:
    if requested and requested.strip():
        return requested.strip().lower()
    return get_platform_settings()["market_data_provider"]
