import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl, TypeAdapter

from packages.shared.config import DEFAULT_LLM_API_BASE, DEFAULT_LLM_MODEL, settings
from packages.services.news_provider_registry import (
    DEFAULT_NEWS_SEARCH_ENABLED_PROVIDERS,
    DEFAULT_NEWS_SEARCH_MAX_RESULTS,
    DEFAULT_NEWS_SEARCH_PROVIDER_ORDER,
    DEFAULT_NEWS_SEARCH_TIMEOUT_SECONDS,
    build_news_search_provider_capabilities,
    merge_news_search_provider_keys,
    normalize_news_search_enabled_providers,
    normalize_news_search_max_results,
    normalize_news_search_provider_keys,
    normalize_news_search_provider_order,
    normalize_news_search_timeout_seconds,
)

SETTINGS_PATH = Path(__file__).resolve().parents[2] / "data" / "platform_settings.json"
_HTTP_URL_ADAPTER = TypeAdapter(AnyHttpUrl)

DEFAULT_FAVORITE_MACRO_INDICATOR_CODES = [
    "buffett_indicator_us",
    "buffett_indicator_cn",
    "buffett_indicator_hk",
    "us_10y_yield",
    "us_10y_2y_spread",
    "us_cpi_yoy",
    "us_m2_yoy",
    "cn_m2_yoy",
]

DEFAULTS: dict[str, Any] = {
    "market_data_provider": settings.market_data_provider,
    "llm_provider": settings.llm_provider,
    "llm_api_key": settings.llm_api_key or "",
    "llm_api_base": settings.llm_api_base,
    "llm_model": settings.llm_model,
    "akshare_enabled": False,
    "tushare_token": "",
    "tushare_http_url": "",
    "eastmoney_proxy_url": "",
    "eastmoney_cookie": "",
    "color_scheme": "china",
    "favorite_macro_indicator_codes": DEFAULT_FAVORITE_MACRO_INDICATOR_CODES,
    "news_search_provider_order": DEFAULT_NEWS_SEARCH_PROVIDER_ORDER,
    "news_search_enabled_providers": DEFAULT_NEWS_SEARCH_ENABLED_PROVIDERS,
    "news_search_provider_keys": {},
    "news_search_max_results": DEFAULT_NEWS_SEARCH_MAX_RESULTS,
    "news_search_timeout_seconds": DEFAULT_NEWS_SEARCH_TIMEOUT_SECONDS,
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


def normalize_favorite_macro_indicator_codes(value: Any) -> list[str]:
    if isinstance(value, list):
        raw_codes = [str(item) for item in value]
    elif isinstance(value, str):
        raw_codes = value.replace(",", "\n").splitlines()
    else:
        raw_codes = []

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_code in raw_codes:
        code = raw_code.strip()
        if not code or code in seen:
            continue
        normalized.append(code)
        seen.add(code)
    return normalized


def is_valid_llm_api_base(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().rstrip("/")
    if "\\" in normalized or any(
        character.isspace() or ord(character) < 32 or ord(character) == 127
        for character in normalized
    ):
        return False
    authority = normalized.partition("://")[2].partition("/")[0]
    if not authority or "%" in authority:
        return False
    try:
        parsed = urlsplit(normalized)
        parsed.port
        _HTTP_URL_ADAPTER.validate_python(normalized)
    except (TypeError, ValueError):
        return False
    return bool(
        parsed.scheme in {"http", "https"}
        and parsed.hostname
        and not parsed.username
        and not parsed.password
        and "?" not in normalized
        and "#" not in normalized
    )


def normalize_llm_api_base(
    value: Any,
    *,
    fallback: Any = DEFAULT_LLM_API_BASE,
) -> str:
    normalized = value.strip().rstrip("/") if isinstance(value, str) else ""
    normalized_fallback = fallback.strip().rstrip("/") if isinstance(fallback, str) else ""
    if not is_valid_llm_api_base(normalized_fallback):
        normalized_fallback = DEFAULT_LLM_API_BASE
    return normalized if is_valid_llm_api_base(normalized) else normalized_fallback


def has_invalid_explicit_llm_api_base(value: Any) -> bool:
    if value is None:
        return False
    if not isinstance(value, str):
        return True
    normalized = value.strip().rstrip("/")
    return bool(normalized) and not is_valid_llm_api_base(normalized)


def normalize_llm_model(
    value: Any,
    *,
    fallback: Any = DEFAULT_LLM_MODEL,
) -> str:
    normalized_fallback = fallback.strip() if isinstance(fallback, str) else ""
    if not normalized_fallback:
        normalized_fallback = DEFAULT_LLM_MODEL
    if not isinstance(value, str):
        return normalized_fallback
    return value.strip() or normalized_fallback


if has_invalid_explicit_llm_api_base(DEFAULTS["llm_api_base"]):
    DEFAULTS["llm_provider"] = "mock"
    DEFAULTS["llm_api_key"] = ""
    DEFAULTS["llm_api_base"] = DEFAULT_LLM_API_BASE


def get_platform_settings() -> dict[str, Any]:
    payload = dict(DEFAULTS)
    if SETTINGS_PATH.exists():
        try:
            stored = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(stored, dict):
                payload.update({key: stored[key] for key in DEFAULTS if key in stored})
        except json.JSONDecodeError:
            pass
    llm_provider = str(payload["llm_provider"]).lower()
    raw_llm_api_base = payload.get("llm_api_base")
    invalid_llm_api_base = has_invalid_explicit_llm_api_base(raw_llm_api_base)
    if invalid_llm_api_base:
        llm_provider = "mock"
    return {
        "market_data_provider": str(payload["market_data_provider"]).lower(),
        "llm_provider": llm_provider,
        "llm_api_key": (
            payload["llm_api_key"]
            if not invalid_llm_api_base and isinstance(payload["llm_api_key"], str)
            else ""
        ),
        "llm_api_base": normalize_llm_api_base(
            raw_llm_api_base,
            fallback=DEFAULTS["llm_api_base"],
        ),
        "llm_model": normalize_llm_model(
            payload.get("llm_model"),
            fallback=DEFAULTS["llm_model"],
        ),
        "akshare_enabled": bool(payload.get("akshare_enabled", False)),
        "tushare_token": str(payload.get("tushare_token", "") or ""),
        "tushare_http_url": str(payload.get("tushare_http_url", "") or ""),
        "eastmoney_proxy_url": str(payload.get("eastmoney_proxy_url", "") or ""),
        "eastmoney_cookie": str(payload.get("eastmoney_cookie", "") or ""),
        "color_scheme": str(payload.get("color_scheme", "china")),
        "favorite_macro_indicator_codes": normalize_favorite_macro_indicator_codes(
            payload.get("favorite_macro_indicator_codes", DEFAULT_FAVORITE_MACRO_INDICATOR_CODES)
        ),
        "news_search_provider_order": normalize_news_search_provider_order(
            payload.get("news_search_provider_order", DEFAULT_NEWS_SEARCH_PROVIDER_ORDER)
        ),
        "news_search_enabled_providers": normalize_news_search_enabled_providers(
            payload.get("news_search_enabled_providers", DEFAULT_NEWS_SEARCH_ENABLED_PROVIDERS)
        ),
        "news_search_provider_keys": normalize_news_search_provider_keys(
            payload.get("news_search_provider_keys", {})
        ),
        "news_search_max_results": normalize_news_search_max_results(
            payload.get("news_search_max_results", DEFAULT_NEWS_SEARCH_MAX_RESULTS)
        ),
        "news_search_timeout_seconds": normalize_news_search_timeout_seconds(
            payload.get("news_search_timeout_seconds", DEFAULT_NEWS_SEARCH_TIMEOUT_SECONDS)
        ),
    }


def get_platform_settings_public() -> dict[str, Any]:
    current = get_platform_settings()
    api_key = current["llm_api_key"]
    tushare_token = current["tushare_token"]
    tushare_http_url = current["tushare_http_url"]
    eastmoney_proxy_url = current["eastmoney_proxy_url"]
    eastmoney_cookie = current["eastmoney_cookie"]
    color_scheme = current["color_scheme"]
    news_search_provider_keys = current["news_search_provider_keys"]
    news_search_provider_keys_configured = {
        provider: bool(str(api_key).strip())
        for provider, api_key in news_search_provider_keys.items()
    }
    return {
        **current,
        "llm_api_key": "",
        "llm_api_key_configured": bool(api_key.strip()),
        "tushare_token": "",
        "tushare_token_configured": bool(tushare_token.strip()),
        "tushare_http_url": tushare_http_url,
        "eastmoney_proxy_url": "",
        "eastmoney_proxy_url_configured": bool(eastmoney_proxy_url.strip()),
        "eastmoney_cookie": "",
        "eastmoney_cookie_configured": bool(eastmoney_cookie.strip()),
        "color_scheme": color_scheme,
        "news_search_provider_keys": {},
        "news_search_provider_keys_configured": news_search_provider_keys_configured,
        "news_search_provider_capabilities": build_news_search_provider_capabilities(current),
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
    previous_llm_api_base = current["llm_api_base"]
    replacement_llm_key = updates.get("llm_api_key")
    has_replacement_llm_key = isinstance(replacement_llm_key, str) and bool(
        replacement_llm_key.strip()
    )
    for key in DEFAULTS:
        if key not in updates or updates[key] is None:
            continue
        if key == "llm_api_key" and not str(updates[key]).strip():
            continue
        if key in {"eastmoney_proxy_url", "eastmoney_cookie"} and not str(updates[key]).strip():
            continue
        if key == "news_search_provider_keys":
            current[key] = merge_news_search_provider_keys(current[key], updates[key])
            continue
        current[key] = updates[key]
    current["market_data_provider"] = str(current["market_data_provider"]).lower()
    current["llm_provider"] = str(current["llm_provider"]).lower()
    if has_invalid_explicit_llm_api_base(current.get("llm_api_base")):
        current["llm_provider"] = "mock"
        current["llm_api_key"] = ""
    current["llm_api_base"] = normalize_llm_api_base(
        current.get("llm_api_base"),
        fallback=DEFAULTS["llm_api_base"],
    )
    if current["llm_api_base"] != previous_llm_api_base and not has_replacement_llm_key:
        current["llm_api_key"] = ""
    if not isinstance(current.get("llm_api_key"), str):
        current["llm_api_key"] = ""
    current["llm_model"] = normalize_llm_model(
        current.get("llm_model"),
        fallback=DEFAULTS["llm_model"],
    )
    current["akshare_enabled"] = bool(current.get("akshare_enabled", False))
    current["tushare_token"] = str(current.get("tushare_token", "") or "")
    current["tushare_http_url"] = str(current.get("tushare_http_url", "") or "")
    current["eastmoney_proxy_url"] = str(current.get("eastmoney_proxy_url", "") or "")
    current["eastmoney_cookie"] = str(current.get("eastmoney_cookie", "") or "")
    current["color_scheme"] = str(current.get("color_scheme", "china"))
    current["favorite_macro_indicator_codes"] = normalize_favorite_macro_indicator_codes(
        current.get("favorite_macro_indicator_codes", DEFAULT_FAVORITE_MACRO_INDICATOR_CODES)
    )
    current["news_search_provider_order"] = normalize_news_search_provider_order(
        current.get("news_search_provider_order", DEFAULT_NEWS_SEARCH_PROVIDER_ORDER)
    )
    current["news_search_enabled_providers"] = normalize_news_search_enabled_providers(
        current.get("news_search_enabled_providers", DEFAULT_NEWS_SEARCH_ENABLED_PROVIDERS)
    )
    current["news_search_provider_keys"] = normalize_news_search_provider_keys(
        current.get("news_search_provider_keys", {})
    )
    current["news_search_max_results"] = normalize_news_search_max_results(
        current.get("news_search_max_results", DEFAULT_NEWS_SEARCH_MAX_RESULTS)
    )
    current["news_search_timeout_seconds"] = normalize_news_search_timeout_seconds(
        current.get("news_search_timeout_seconds", DEFAULT_NEWS_SEARCH_TIMEOUT_SECONDS)
    )
    _ensure_parent()
    SETTINGS_PATH.write_text(json.dumps(current, indent=2), encoding="utf-8")
    return get_platform_settings_public()


def get_effective_market_data_provider(requested: str | None = None) -> str:
    if requested and requested.strip():
        return requested.strip().lower()
    return get_platform_settings()["market_data_provider"]
