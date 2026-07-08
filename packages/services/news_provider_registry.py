from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEFAULT_NEWS_SEARCH_MAX_RESULTS = 10
DEFAULT_NEWS_SEARCH_TIMEOUT_SECONDS = 8.0


@dataclass(frozen=True)
class NewsSearchProviderSpec:
    provider: str
    display_name: str
    credential_required: bool
    credential_field: str | None
    supported_markets: tuple[str, ...]
    supported_regions: tuple[str, ...]
    supported_result_kinds: tuple[str, ...]
    default_timeout_seconds: float
    default_max_results: int
    implementation_status: str
    readiness_note: str
    citation_caveat: str


NEWS_SEARCH_PROVIDER_SPECS: tuple[NewsSearchProviderSpec, ...] = (
    NewsSearchProviderSpec(
        provider="anspire",
        display_name="Anspire AI Search",
        credential_required=True,
        credential_field="api_key",
        supported_markets=("A-share", "US", "HK", "global"),
        supported_regions=("CN", "US", "HK", "global"),
        supported_result_kinds=("news", "web", "public_opinion"),
        default_timeout_seconds=DEFAULT_NEWS_SEARCH_TIMEOUT_SECONDS,
        default_max_results=DEFAULT_NEWS_SEARCH_MAX_RESULTS,
        implementation_status="implemented",
        readiness_note="Bearer-auth search adapter for financial news and public opinion.",
        citation_caveat="Search results become citable only after they are stored as local news.",
    ),
    NewsSearchProviderSpec(
        provider="serpapi_baidu",
        display_name="SerpAPI Baidu",
        credential_required=True,
        credential_field="api_key",
        supported_markets=("A-share", "HK", "China"),
        supported_regions=("CN",),
        supported_result_kinds=("news", "web", "social"),
        default_timeout_seconds=DEFAULT_NEWS_SEARCH_TIMEOUT_SECONDS,
        default_max_results=DEFAULT_NEWS_SEARCH_MAX_RESULTS,
        implementation_status="implemented",
        readiness_note="Baidu search result adapter for Chinese-market news discovery.",
        citation_caveat="Baidu results are collection candidates until stored locally.",
    ),
    NewsSearchProviderSpec(
        provider="tavily",
        display_name="Tavily",
        credential_required=True,
        credential_field="api_key",
        supported_markets=("global",),
        supported_regions=("global",),
        supported_result_kinds=("news", "web"),
        default_timeout_seconds=DEFAULT_NEWS_SEARCH_TIMEOUT_SECONDS,
        default_max_results=DEFAULT_NEWS_SEARCH_MAX_RESULTS,
        implementation_status="configured_only",
        readiness_note="Registry-only in this slice; a direct adapter can follow later.",
        citation_caveat="Do not cite Tavily results until adapter storage is implemented.",
    ),
    NewsSearchProviderSpec(
        provider="bocha",
        display_name="Bocha Search",
        credential_required=True,
        credential_field="api_key",
        supported_markets=("A-share", "China"),
        supported_regions=("CN",),
        supported_result_kinds=("news", "web", "ai_summary"),
        default_timeout_seconds=DEFAULT_NEWS_SEARCH_TIMEOUT_SECONDS,
        default_max_results=DEFAULT_NEWS_SEARCH_MAX_RESULTS,
        implementation_status="needs_contract",
        readiness_note="Chinese search candidate; endpoint contract needs confirmation.",
        citation_caveat="Keep Bocha as registry-only until API and storage terms are reviewed.",
    ),
    NewsSearchProviderSpec(
        provider="brave",
        display_name="Brave Search",
        credential_required=True,
        credential_field="subscription_token",
        supported_markets=("US", "global"),
        supported_regions=("US", "global"),
        supported_result_kinds=("news", "web"),
        default_timeout_seconds=DEFAULT_NEWS_SEARCH_TIMEOUT_SECONDS,
        default_max_results=DEFAULT_NEWS_SEARCH_MAX_RESULTS,
        implementation_status="configured_only",
        readiness_note="Privacy-oriented search candidate; adapter deferred.",
        citation_caveat="Review plan storage rights before storing Brave result text.",
    ),
    NewsSearchProviderSpec(
        provider="minimax",
        display_name="MiniMax",
        credential_required=True,
        credential_field="api_key",
        supported_markets=("global",),
        supported_regions=("global",),
        supported_result_kinds=("structured_search", "web"),
        default_timeout_seconds=DEFAULT_NEWS_SEARCH_TIMEOUT_SECONDS,
        default_max_results=DEFAULT_NEWS_SEARCH_MAX_RESULTS,
        implementation_status="needs_contract",
        readiness_note="MCP/CLI-oriented search path; backend REST contract is not confirmed.",
        citation_caveat="Keep MiniMax results out of citations until a backend adapter exists.",
    ),
    NewsSearchProviderSpec(
        provider="yfinance",
        display_name="yfinance",
        credential_required=False,
        credential_field=None,
        supported_markets=("US", "global"),
        supported_regions=("US", "global"),
        supported_result_kinds=("news",),
        default_timeout_seconds=DEFAULT_NEWS_SEARCH_TIMEOUT_SECONDS,
        default_max_results=DEFAULT_NEWS_SEARCH_MAX_RESULTS,
        implementation_status="existing",
        readiness_note="Existing news ingestion path; not part of live-search MVP.",
        citation_caveat="Only stored yfinance NewsArticle rows are citable.",
    ),
    NewsSearchProviderSpec(
        provider="akshare",
        display_name="AkShare",
        credential_required=False,
        credential_field=None,
        supported_markets=("A-share", "China"),
        supported_regions=("CN",),
        supported_result_kinds=("news",),
        default_timeout_seconds=DEFAULT_NEWS_SEARCH_TIMEOUT_SECONDS,
        default_max_results=DEFAULT_NEWS_SEARCH_MAX_RESULTS,
        implementation_status="existing",
        readiness_note="Existing CN news ingestion path when AkShare is enabled.",
        citation_caveat="Only stored AkShare NewsArticle rows are citable.",
    ),
    NewsSearchProviderSpec(
        provider="tushare",
        display_name="Tushare",
        credential_required=True,
        credential_field="tushare_token",
        supported_markets=("A-share", "China"),
        supported_regions=("CN",),
        supported_result_kinds=("news",),
        default_timeout_seconds=DEFAULT_NEWS_SEARCH_TIMEOUT_SECONDS,
        default_max_results=DEFAULT_NEWS_SEARCH_MAX_RESULTS,
        implementation_status="existing",
        readiness_note="Existing placeholder requires the saved Tushare token.",
        citation_caveat="Only stored Tushare-backed NewsArticle rows are citable.",
    ),
    NewsSearchProviderSpec(
        provider="mock",
        display_name="Mock news",
        credential_required=False,
        credential_field=None,
        supported_markets=("US", "development"),
        supported_regions=("US",),
        supported_result_kinds=("news",),
        default_timeout_seconds=DEFAULT_NEWS_SEARCH_TIMEOUT_SECONDS,
        default_max_results=DEFAULT_NEWS_SEARCH_MAX_RESULTS,
        implementation_status="mock",
        readiness_note="Deterministic local fixture path for development and tests.",
        citation_caveat="Mock rows are not production evidence.",
    ),
)

NEWS_SEARCH_PROVIDER_REGISTRY = {
    spec.provider: spec for spec in NEWS_SEARCH_PROVIDER_SPECS
}
NEWS_SEARCH_PROVIDER_IDS = tuple(NEWS_SEARCH_PROVIDER_REGISTRY.keys())
DEFAULT_NEWS_SEARCH_PROVIDER_ORDER = list(NEWS_SEARCH_PROVIDER_IDS)
DEFAULT_NEWS_SEARCH_ENABLED_PROVIDERS = ["anspire", "serpapi_baidu"]


def _raw_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if isinstance(value, str):
        return value.replace(",", "\n").splitlines()
    return []


def normalize_news_search_provider_order(value: Any) -> list[str]:
    normalized = _normalize_provider_ids(value)
    if not normalized:
        normalized = list(DEFAULT_NEWS_SEARCH_PROVIDER_ORDER)
    for provider in NEWS_SEARCH_PROVIDER_IDS:
        if provider not in normalized:
            normalized.append(provider)
    return normalized


def normalize_news_search_enabled_providers(value: Any) -> list[str]:
    if value is None:
        return list(DEFAULT_NEWS_SEARCH_ENABLED_PROVIDERS)
    return _normalize_provider_ids(value)


def normalize_news_search_provider_keys(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}

    keys: dict[str, str] = {}
    for provider in NEWS_SEARCH_PROVIDER_IDS:
        raw_value = value.get(provider)
        if raw_value is None:
            continue
        text_value = str(raw_value).strip()
        if text_value:
            keys[provider] = text_value
    return keys


def merge_news_search_provider_keys(current: Any, updates: Any) -> dict[str, str]:
    merged = normalize_news_search_provider_keys(current)
    if not isinstance(updates, dict):
        return merged

    for provider in NEWS_SEARCH_PROVIDER_IDS:
        if provider not in updates:
            continue
        text_value = str(updates.get(provider) or "").strip()
        if text_value:
            merged[provider] = text_value
    return merged


def normalize_news_search_max_results(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return DEFAULT_NEWS_SEARCH_MAX_RESULTS
    return min(max(parsed, 1), 20)


def normalize_news_search_timeout_seconds(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return DEFAULT_NEWS_SEARCH_TIMEOUT_SECONDS
    return min(max(parsed, 1.0), 30.0)


def build_news_search_provider_capabilities(
    settings_payload: dict[str, Any],
) -> list[dict[str, object]]:
    order = normalize_news_search_provider_order(
        settings_payload.get("news_search_provider_order")
    )
    enabled = set(
        normalize_news_search_enabled_providers(
            settings_payload.get("news_search_enabled_providers")
        )
    )
    provider_keys = normalize_news_search_provider_keys(
        settings_payload.get("news_search_provider_keys")
    )
    akshare_enabled = bool(settings_payload.get("akshare_enabled", False))
    tushare_token_configured = bool(
        str(settings_payload.get("tushare_token", "") or "").strip()
    )

    capabilities: list[dict[str, object]] = []
    for provider in order:
        spec = NEWS_SEARCH_PROVIDER_REGISTRY[provider]
        configured = _is_news_search_provider_configured(
            provider,
            provider_keys=provider_keys,
            akshare_enabled=akshare_enabled,
            tushare_token_configured=tushare_token_configured,
        )
        capabilities.append(
            {
                "provider": provider,
                "display_name": spec.display_name,
                "enabled": provider in enabled,
                "configured": configured,
                "credential_required": spec.credential_required,
                "credential_configured": configured if spec.credential_required else True,
                "credential_field": spec.credential_field,
                "priority": order.index(provider) + 1,
                "supported_markets": list(spec.supported_markets),
                "supported_regions": list(spec.supported_regions),
                "supported_result_kinds": list(spec.supported_result_kinds),
                "default_timeout_seconds": spec.default_timeout_seconds,
                "default_max_results": spec.default_max_results,
                "implementation_status": spec.implementation_status,
                "readiness_note": spec.readiness_note,
                "citation_caveat": spec.citation_caveat,
            }
        )
    return capabilities


def _normalize_provider_ids(value: Any) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_provider in _raw_string_list(value):
        provider = raw_provider.strip().lower()
        if (
            not provider
            or provider in seen
            or provider not in NEWS_SEARCH_PROVIDER_REGISTRY
        ):
            continue
        normalized.append(provider)
        seen.add(provider)
    return normalized


def _is_news_search_provider_configured(
    provider: str,
    *,
    provider_keys: dict[str, str],
    akshare_enabled: bool,
    tushare_token_configured: bool,
) -> bool:
    if provider == "akshare":
        return akshare_enabled
    if provider == "tushare":
        return tushare_token_configured
    spec = NEWS_SEARCH_PROVIDER_REGISTRY[provider]
    if not spec.credential_required:
        return True
    return bool(provider_keys.get(provider))
