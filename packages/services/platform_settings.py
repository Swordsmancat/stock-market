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
    "tushare_http_url": "",
    "color_scheme": "china",
}


MARKET_DATA_PROVIDER_CAPABILITY_BASE: dict[str, dict[str, object]] = {
    "mock": {
        "category": "mock",
        "supports_daily_bars": True,
        "supports_realtime_quotes": False,
        "readiness_note": "Deterministic fixture data for development and tests.",
    },
    "yfinance": {
        "category": "historical_daily",
        "supports_daily_bars": True,
        "supports_realtime_quotes": False,
        "readiness_note": "Historical daily bars are available; real-time quotes are not enabled.",
    },
    "akshare": {
        "category": "historical_daily",
        "supports_daily_bars": True,
        "supports_realtime_quotes": False,
        "readiness_note": "Requires AkShare support to be enabled and dependencies installed.",
    },
    "tushare": {
        "category": "historical_daily",
        "supports_daily_bars": True,
        "supports_realtime_quotes": False,
        "readiness_note": "Requires a configured Tushare token.",
    },
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
        "tushare_http_url": str(payload.get("tushare_http_url", "") or ""),
        "color_scheme": str(payload.get("color_scheme", "china")),
    }


def get_platform_settings_public() -> dict[str, Any]:
    current = get_platform_settings()
    api_key = current["llm_api_key"]
    tushare_token = current["tushare_token"]
    tushare_http_url = current["tushare_http_url"]
    color_scheme = current["color_scheme"]
    return {
        **current,
        "llm_api_key": api_key,
        "llm_api_key_configured": bool(api_key.strip()),
        "tushare_token": "",
        "tushare_token_configured": bool(tushare_token.strip()),
        "tushare_http_url": tushare_http_url,
        "color_scheme": color_scheme,
        "market_data_provider_capabilities": build_market_data_provider_capabilities(current),
    }


def build_market_data_provider_capabilities(settings_payload: dict[str, Any]) -> list[dict[str, object]]:
    active_provider = str(settings_payload["market_data_provider"]).lower()
    akshare_enabled = bool(settings_payload.get("akshare_enabled", False))
    tushare_token_configured = bool(str(settings_payload.get("tushare_token", "") or "").strip())

    capabilities: list[dict[str, object]] = []
    for provider_name, base_capability in MARKET_DATA_PROVIDER_CAPABILITY_BASE.items():
        configured = _is_market_data_provider_configured(
            provider_name,
            akshare_enabled=akshare_enabled,
            tushare_token_configured=tushare_token_configured,
        )
        capabilities.append(
            {
                "provider": provider_name,
                "active": provider_name == active_provider,
                "configured": configured,
                **base_capability,
            }
        )
    return capabilities


def _is_market_data_provider_configured(
    provider_name: str,
    *,
    akshare_enabled: bool,
    tushare_token_configured: bool,
) -> bool:
    if provider_name in {"mock", "yfinance"}:
        return True
    if provider_name == "akshare":
        return akshare_enabled
    if provider_name == "tushare":
        return tushare_token_configured
    return False


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
    current["tushare_http_url"] = str(current.get("tushare_http_url", "") or "")
    current["color_scheme"] = str(current.get("color_scheme", "china"))
    _ensure_parent()
    SETTINGS_PATH.write_text(json.dumps(current, indent=2), encoding="utf-8")
    return get_platform_settings_public()


def get_effective_market_data_provider(requested: str | None = None) -> str:
    if requested and requested.strip():
        return requested.strip().lower()
    return get_platform_settings()["market_data_provider"]
