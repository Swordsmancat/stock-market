from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.analytics.sentiment import make_dedupe_hash
from packages.providers.cn_market_helpers import find_column, normalize_cn_symbol
from packages.providers.yfinance_helpers import map_symbol_to_ticker
from packages.services.news import (
    build_empty_news_sentiment_payload,
    get_news_sentiment_payload,
    is_supported_news_identity,
    normalize_news_article_fields,
    persist_normalized_news_article,
)
from packages.services.news_provider_registry import (
    NEWS_SEARCH_PROVIDER_REGISTRY,
    build_news_search_provider_capabilities,
    normalize_news_search_enabled_providers,
    normalize_news_search_max_results,
    normalize_news_search_provider_order,
    normalize_news_search_timeout_seconds,
)
from packages.services.platform_settings import get_platform_settings


ANSPIRE_SEARCH_ENDPOINT = "https://plugin.anspire.cn/api/ntsearch/search"
SERPAPI_BAIDU_SEARCH_ENDPOINT = "https://serpapi.com/search.json"
PERSISTABLE_NEWS_RESULT_KINDS = {"news", "web"}
SOCIAL_SENTIMENT_RESULT_KINDS = {"public_opinion", "social"}
REFRESH_BUILTIN_PROVIDER_IDS = {"akshare", "mock", "tushare", "yfinance"}
SUPPORTED_YFINANCE_NEWS_MARKETS = {"CN", "HK", "US"}
HttpGetter = Callable[..., object]


class NewsSearchProviderError(RuntimeError):
    """Sanitized provider error for news-search adapters."""


class NewsSearchProviderTimeout(NewsSearchProviderError):
    """Raised when a provider request times out."""


class NewsSearchAdapter(Protocol):
    provider: str

    def search(
        self,
        *,
        symbol: str,
        query: str,
        max_results: int,
    ) -> list["NewsSearchCandidate"]:
        ...


@dataclass(frozen=True)
class NewsSearchDiagnostic:
    provider: str
    status: str
    severity: str
    code: str
    message: str
    details: dict[str, object] = field(default_factory=dict)

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "provider": self.provider,
            "status": self.status,
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        return payload


@dataclass(frozen=True)
class NewsSearchCandidate:
    symbol: str
    query: str
    title: str
    url: str
    source: str
    summary: str | None
    published_at: datetime | None
    retrieved_at: datetime
    provider: str
    language: str | None = None
    region: str | None = None
    score: float | None = None
    result_kind: str = "news"
    diagnostics: tuple[NewsSearchDiagnostic, ...] = ()

    def to_payload(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "query": self.query,
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "summary": self.summary,
            "published_at": _isoformat_or_none(self.published_at),
            "retrieved_at": _isoformat_datetime(self.retrieved_at),
            "provider": self.provider,
            "language": self.language,
            "region": self.region,
            "score": self.score,
            "result_kind": self.result_kind,
            "evidence_boundary": _candidate_evidence_boundary(self.result_kind),
            "diagnostics": [
                diagnostic.to_payload() for diagnostic in self.diagnostics
            ],
        }


class AnspireNewsSearchAdapter:
    provider = "anspire"

    def __init__(
        self,
        *,
        api_key: str,
        api_base_url: str = ANSPIRE_SEARCH_ENDPOINT,
        http_getter: HttpGetter | None = None,
        timeout: float = 8.0,
    ) -> None:
        self._api_key = api_key.strip()
        self._api_base_url = api_base_url
        self._http_getter = http_getter or _default_http_getter
        self._timeout = timeout

    def search(
        self,
        *,
        symbol: str,
        query: str,
        max_results: int,
    ) -> list[NewsSearchCandidate]:
        payload = self._request_payload(query=query, max_results=max_results)
        raw_results = _extract_result_rows(payload)
        return _normalize_generic_result_rows(
            raw_results,
            symbol=symbol,
            query=query,
            provider=self.provider,
            default_source="Anspire AI Search",
            default_region=None,
            default_language=None,
            default_result_kind="news",
            max_results=max_results,
        )

    def _request_payload(self, *, query: str, max_results: int) -> object:
        params = {"query": query, "top_k": max_results}
        headers = {"Authorization": f"Bearer {self._api_key}"}
        return _request_json_payload(
            provider=self.provider,
            url=self._api_base_url,
            http_getter=self._http_getter,
            timeout=self._timeout,
            params=params,
            headers=headers,
        )


class SerpApiBaiduNewsSearchAdapter:
    provider = "serpapi_baidu"

    def __init__(
        self,
        *,
        api_key: str,
        api_base_url: str = SERPAPI_BAIDU_SEARCH_ENDPOINT,
        http_getter: HttpGetter | None = None,
        timeout: float = 8.0,
    ) -> None:
        self._api_key = api_key.strip()
        self._api_base_url = api_base_url
        self._http_getter = http_getter or _default_http_getter
        self._timeout = timeout

    def search(
        self,
        *,
        symbol: str,
        query: str,
        max_results: int,
    ) -> list[NewsSearchCandidate]:
        payload = self._request_payload(query=query, max_results=max_results)
        if not isinstance(payload, Mapping):
            raise NewsSearchProviderError("SerpAPI Baidu response was not a JSON object.")

        rows: list[tuple[Mapping[str, Any], str]] = []
        rows.extend(_extract_named_rows(payload, "news_results", "news"))
        rows.extend(_extract_named_rows(payload, "organic_results", "web"))
        rows.extend(_extract_named_rows(payload, "social_results", "social"))
        rows.extend(_extract_named_rows(payload, "media_results", "media"))

        candidates: list[NewsSearchCandidate] = []
        for raw_row, result_kind in rows[:max_results]:
            candidate = _normalize_search_row(
                raw_row,
                symbol=symbol,
                query=query,
                provider=self.provider,
                default_source="SerpAPI Baidu",
                default_region="CN",
                default_language="zh",
                default_result_kind=result_kind,
            )
            if candidate is not None:
                candidates.append(candidate)
        return candidates

    def _request_payload(self, *, query: str, max_results: int) -> object:
        params = {
            "engine": "baidu",
            "q": query,
            "api_key": self._api_key,
            "num": max_results,
        }
        return _request_json_payload(
            provider=self.provider,
            url=self._api_base_url,
            http_getter=self._http_getter,
            timeout=self._timeout,
            params=params,
        )


class AkShareNewsSearchAdapter:
    provider = "akshare"

    def __init__(self, *, fetcher: Callable[[str], object] | None = None) -> None:
        self._fetcher = fetcher or _default_akshare_news_fetcher

    def search(
        self,
        *,
        symbol: str,
        query: str,
        max_results: int,
    ) -> list[NewsSearchCandidate]:
        frame = self._fetcher(normalize_cn_symbol(symbol))
        if frame is None or bool(getattr(frame, "empty", False)):
            return []
        columns = [str(column) for column in getattr(frame, "columns", [])]
        title_column = find_column(columns, "新闻标题") or find_column(columns, "标题")
        url_column = find_column(columns, "新闻链接") or find_column(columns, "链接")
        if title_column is None or url_column is None:
            raise NewsSearchProviderError(
                "AkShare news response did not contain title and URL columns."
            )
        published_column = find_column(columns, "发布时间")
        source_column = find_column(columns, "文章来源") or find_column(columns, "来源")
        summary_column = find_column(columns, "新闻内容") or find_column(columns, "内容")
        try:
            rows = frame.head(max_results).iterrows()
        except (AttributeError, TypeError) as error:
            raise NewsSearchProviderError(
                "AkShare news response was not a supported table."
            ) from error

        retrieved_at = datetime.now(timezone.utc)
        candidates: list[NewsSearchCandidate] = []
        for _, row in rows:
            title = _frame_text(row[title_column])
            url = _frame_text(row[url_column])
            if title is None or url is None:
                continue
            summary = _frame_text(row[summary_column]) if summary_column else None
            source = _frame_text(row[source_column]) if source_column else None
            candidates.append(
                NewsSearchCandidate(
                    symbol=symbol.strip().upper(),
                    query=query,
                    title=title,
                    url=url,
                    source=source or "AkShare",
                    summary=summary or title,
                    published_at=(
                        _parse_cn_news_datetime(row[published_column])
                        if published_column
                        else None
                    ),
                    retrieved_at=retrieved_at,
                    provider=self.provider,
                    language="zh",
                    region="CN",
                )
            )
        return candidates


class YFinanceNewsSearchAdapter:
    provider = "yfinance"

    def __init__(
        self,
        *,
        market: str,
        ticker_factory: Callable[[str], object] | None = None,
    ) -> None:
        self._market = market.strip().upper()
        self._ticker_factory = ticker_factory or _default_yfinance_ticker_factory

    def search(
        self,
        *,
        symbol: str,
        query: str,
        max_results: int,
    ) -> list[NewsSearchCandidate]:
        ticker_symbol = map_symbol_to_ticker(symbol, self._market)
        ticker = self._ticker_factory(ticker_symbol)
        get_news = getattr(ticker, "get_news", None)
        rows = (
            get_news(count=max_results)
            if callable(get_news)
            else getattr(ticker, "news", None)
        )
        if rows is None:
            return []
        if not isinstance(rows, list):
            raise NewsSearchProviderError(
                "yfinance news response was not a supported list."
            )

        retrieved_at = datetime.now(timezone.utc)
        candidates: list[NewsSearchCandidate] = []
        for row in rows[:max_results]:
            if not isinstance(row, Mapping):
                continue
            content_value = row.get("content")
            content = content_value if isinstance(content_value, Mapping) else {}
            title = _first_text(content, ("title", "headline")) or _first_text(
                row, ("title", "headline")
            )
            url = _nested_mapping_text(
                content,
                ("canonicalUrl", "clickThroughUrl"),
                ("url",),
            ) or _first_text(row, ("link", "url"))
            if title is None or url is None:
                continue
            provider_name = _nested_mapping_text(
                content,
                ("provider",),
                ("displayName", "name"),
            ) or _first_text(row, ("publisher", "source"))
            summary = _first_text(
                content, ("summary", "description")
            ) or _first_text(row, ("summary", "description"))
            published_value = _first_value(
                content,
                ("pubDate", "displayTime", "published_at"),
            ) or _first_value(row, ("providerPublishTime", "published_at"))
            candidates.append(
                NewsSearchCandidate(
                    symbol=symbol.strip().upper(),
                    query=query,
                    title=title,
                    url=url,
                    source=provider_name or "yfinance",
                    summary=summary or title,
                    published_at=_parse_datetime(published_value),
                    retrieved_at=retrieved_at,
                    provider=self.provider,
                    region=self._market,
                )
            )
        return candidates


def search_news_candidates(
    symbol: str,
    *,
    session: Session | None = None,
    query: str | None = None,
    settings_payload: dict[str, Any] | None = None,
    adapters: Mapping[str, NewsSearchAdapter] | None = None,
) -> dict[str, object]:
    resolved_settings = settings_payload or get_platform_settings()
    normalized_symbol = symbol.strip().upper()
    resolved_query = query.strip() if query and query.strip() else _default_news_query(normalized_symbol)
    max_results = normalize_news_search_max_results(
        resolved_settings.get("news_search_max_results")
    )
    timeout_seconds = normalize_news_search_timeout_seconds(
        resolved_settings.get("news_search_timeout_seconds")
    )
    order = normalize_news_search_provider_order(
        resolved_settings.get("news_search_provider_order")
    )
    enabled = set(
        normalize_news_search_enabled_providers(
            resolved_settings.get("news_search_enabled_providers")
        )
    )
    provider_keys = resolved_settings.get("news_search_provider_keys")
    provider_key_map = provider_keys if isinstance(provider_keys, dict) else {}

    diagnostics: list[NewsSearchDiagnostic] = []
    candidates: list[NewsSearchCandidate] = []

    for provider in order:
        spec = NEWS_SEARCH_PROVIDER_REGISTRY[provider]
        if provider not in enabled:
            diagnostics.append(
                _diagnostic(
                    provider,
                    "skipped",
                    "info",
                    "PROVIDER_DISABLED",
                    f"{spec.display_name} is disabled in news search settings.",
                )
            )
            continue

        if spec.implementation_status != "implemented":
            diagnostics.append(
                _diagnostic(
                    provider,
                    "skipped",
                    "info",
                    "PROVIDER_NOT_IMPLEMENTED",
                    (
                        f"{spec.display_name} is registered as "
                        f"{spec.implementation_status}, not a live-search adapter."
                    ),
                )
            )
            continue

        api_key = str(provider_key_map.get(provider, "") or "").strip()
        if spec.credential_required and not api_key:
            diagnostics.append(
                _diagnostic(
                    provider,
                    "skipped",
                    "warning",
                    "MISSING_CREDENTIALS",
                    f"{spec.display_name} requires a configured API key.",
                )
            )
            continue

        adapter = (
            adapters.get(provider)
            if adapters is not None and provider in adapters
            else _build_adapter(provider, api_key=api_key, timeout=timeout_seconds)
        )
        try:
            provider_candidates = adapter.search(
                symbol=normalized_symbol,
                query=resolved_query,
                max_results=max_results,
            )
        except NewsSearchProviderTimeout:
            diagnostics.append(
                _diagnostic(
                    provider,
                    "timeout",
                    "warning",
                    "PROVIDER_TIMEOUT",
                    f"{spec.display_name} timed out while searching news.",
                )
            )
            continue
        except NewsSearchProviderError as error:
            diagnostics.append(
                _diagnostic(
                    provider,
                    "error",
                    "warning",
                    "PROVIDER_ERROR",
                    str(error),
                )
            )
            continue
        except Exception as error:
            diagnostics.append(
                _diagnostic(
                    provider,
                    "error",
                    "warning",
                    "PROVIDER_ERROR",
                    f"{spec.display_name} failed with {type(error).__name__}.",
                )
            )
            continue

        if not isinstance(provider_candidates, list):
            diagnostics.append(
                _diagnostic(
                    provider,
                    "error",
                    "warning",
                    "PROVIDER_ERROR",
                    f"{spec.display_name} returned an unsupported candidate payload.",
                )
            )
            continue

        normalized_candidates = _normalize_news_candidate_batch(
            provider_candidates[:max_results],
            requested_symbol=normalized_symbol,
            expected_provider=provider,
        )
        if normalized_candidates is None:
            diagnostics.append(
                _diagnostic(
                    provider,
                    "error",
                    "warning",
                    "PROVIDER_INVALID_CANDIDATE",
                    f"{spec.display_name} returned an invalid news candidate.",
                )
            )
            continue
        provider_candidates = normalized_candidates

        if not provider_candidates:
            diagnostics.append(
                _diagnostic(
                    provider,
                    "empty",
                    "info",
                    "EMPTY_RESPONSE",
                    f"{spec.display_name} returned no usable news candidates.",
                )
            )
            continue

        candidates.extend(provider_candidates)
        diagnostics.append(
            _diagnostic(
                provider,
                "ok",
                "info",
                "PROVIDER_OK",
                f"{spec.display_name} returned {len(provider_candidates)} candidates.",
                details={"candidate_count": len(provider_candidates)},
            )
        )

    deduped_candidates = _dedupe_candidates(candidates)
    database_fallback = _database_fallback_payload(
        normalized_symbol,
        session=session,
        diagnostics=diagnostics,
        live_candidate_count=len(deduped_candidates),
    )
    status = _search_status(deduped_candidates, database_fallback)

    return {
        "symbol": normalized_symbol,
        "query": resolved_query,
        "status": status,
        "candidates": [candidate.to_payload() for candidate in deduped_candidates],
        "candidate_count": len(deduped_candidates),
        "database_fallback": database_fallback,
        "diagnostics": [diagnostic.to_payload() for diagnostic in diagnostics],
        "provider_capabilities": build_news_search_provider_capabilities(resolved_settings),
        "safety": {
            "search_results_are_collection_candidates": True,
            "stored_news_only_is_citable": True,
            "social_sentiment_separated": True,
            "social_results_require_review": True,
            "no_fabricated_news": True,
        },
    }


def search_and_ingest_news_candidates(
    symbol: str,
    *,
    session: Session,
    query: str | None = None,
    settings_payload: dict[str, Any] | None = None,
    adapters: Mapping[str, NewsSearchAdapter] | None = None,
) -> dict[str, object]:
    payload = search_news_candidates(
        symbol,
        session=session,
        query=query,
        settings_payload=settings_payload,
        adapters=adapters,
    )
    candidates = [
        _candidate_from_payload(candidate_payload)
        for candidate_payload in payload["candidates"]
        if isinstance(candidate_payload, dict)
    ]
    social_candidate_count = sum(
        1 for candidate in candidates if _is_social_sentiment_candidate(candidate)
    )
    article_count, sentiment_count = persist_news_search_candidates(
        candidates,
        session=session,
        expected_symbol=symbol.strip().upper(),
    )
    return {
        **payload,
        "status": "ingested" if article_count > 0 else payload["status"],
        "article_count": article_count,
        "sentiment_count": sentiment_count,
        "social_candidate_count": social_candidate_count,
        "social_candidates_deferred": social_candidate_count > 0,
    }


def refresh_news_candidates(
    symbol: str,
    *,
    market: str,
    session: Session,
    settings_payload: dict[str, Any] | None = None,
    adapters: Mapping[str, NewsSearchAdapter] | None = None,
) -> dict[str, object]:
    normalized_symbol = symbol.strip().upper()
    normalized_market = market.strip().upper()
    if not is_supported_news_identity(normalized_symbol, normalized_market):
        return {
            "symbol": normalized_symbol,
            "market": normalized_market,
            "status": "unsupported",
            "selected_provider": None,
            "persisted_article_count": 0,
            "persisted_sentiment_count": 0,
            "attempts": [],
            "diagnostics": [
                _refresh_diagnostic(
                    "identity",
                    "unsupported",
                    "info",
                    "UNSUPPORTED_IDENTITY",
                )
            ],
            "news": build_empty_news_sentiment_payload(normalized_symbol),
        }
    stored_news = get_news_sentiment_payload(
        normalized_symbol,
        session=session,
        market=normalized_market,
    )
    article_count = _news_article_count(stored_news)
    if article_count > 0:
        return {
            "symbol": normalized_symbol,
            "market": normalized_market,
            "status": "database_hit",
            "selected_provider": "database",
            "persisted_article_count": 0,
            "persisted_sentiment_count": 0,
            "attempts": [],
            "diagnostics": [
                _refresh_diagnostic(
                    "database",
                    "ok",
                    "info",
                    "DATABASE_HIT",
                    details={"article_count": article_count},
                )
            ],
            "news": stored_news,
        }

    resolved_settings = (
        settings_payload if settings_payload is not None else get_platform_settings()
    )
    order = normalize_news_search_provider_order(
        resolved_settings.get("news_search_provider_order")
    )
    enabled = set(
        normalize_news_search_enabled_providers(
            resolved_settings.get("news_search_enabled_providers")
        )
    )
    provider_keys = resolved_settings.get("news_search_provider_keys")
    provider_key_map = provider_keys if isinstance(provider_keys, dict) else {}
    max_results = normalize_news_search_max_results(
        resolved_settings.get("news_search_max_results")
    )
    timeout_seconds = normalize_news_search_timeout_seconds(
        resolved_settings.get("news_search_timeout_seconds")
    )
    attempts: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []
    had_provider_error = False

    for provider in order:
        if provider in REFRESH_BUILTIN_PROVIDER_IDS or provider not in enabled:
            continue
        spec = NEWS_SEARCH_PROVIDER_REGISTRY[provider]
        if spec.implementation_status != "implemented":
            continue
        api_key = str(provider_key_map.get(provider, "") or "").strip()
        if spec.credential_required and not api_key:
            diagnostics.append(
                _refresh_diagnostic(provider, "skipped", "warning", "MISSING_CREDENTIALS")
            )
            continue
        adapter = (
            adapters[provider]
            if adapters is not None and provider in adapters
            else _build_adapter(provider, api_key=api_key, timeout=timeout_seconds)
        )
        success_payload, provider_failed = _run_refresh_source(
            adapter,
            provider=provider,
            symbol=normalized_symbol,
            market=normalized_market,
            max_results=max_results,
            session=session,
            attempts=attempts,
            diagnostics=diagnostics,
        )
        if success_payload is not None:
            return success_payload
        had_provider_error = had_provider_error or provider_failed

    if _is_exact_cn_stock(normalized_symbol, normalized_market):
        if bool(resolved_settings.get("akshare_enabled", False)):
            akshare_adapter = (
                adapters["akshare"]
                if adapters is not None and "akshare" in adapters
                else AkShareNewsSearchAdapter()
            )
            success_payload, provider_failed = _run_refresh_source(
                akshare_adapter,
                provider="akshare",
                symbol=normalized_symbol,
                market=normalized_market,
                max_results=max_results,
                session=session,
                attempts=attempts,
                diagnostics=diagnostics,
            )
            if success_payload is not None:
                return success_payload
            had_provider_error = had_provider_error or provider_failed
        else:
            diagnostics.append(
                _refresh_diagnostic(
                    "akshare", "skipped", "info", "PROVIDER_DISABLED"
                )
            )

    unsupported_market = normalized_market not in SUPPORTED_YFINANCE_NEWS_MARKETS
    if not unsupported_market:
        yfinance_adapter = (
            adapters["yfinance"]
            if adapters is not None and "yfinance" in adapters
            else YFinanceNewsSearchAdapter(market=normalized_market)
        )
        success_payload, provider_failed = _run_refresh_source(
            yfinance_adapter,
            provider="yfinance",
            symbol=normalized_symbol,
            market=normalized_market,
            max_results=max_results,
            session=session,
            attempts=attempts,
            diagnostics=diagnostics,
        )
        if success_payload is not None:
            return success_payload
        had_provider_error = had_provider_error or provider_failed
    else:
        diagnostics.append(
            _refresh_diagnostic(
                "yfinance", "skipped", "info", "UNSUPPORTED_MARKET"
            )
        )

    diagnostics.append(
        _refresh_diagnostic("database", "empty", "info", "DATABASE_FALLBACK_EMPTY")
    )
    if had_provider_error:
        final_status = "provider_error"
    elif unsupported_market:
        final_status = "unsupported"
    else:
        final_status = "no_data"
    return {
        "symbol": normalized_symbol,
        "market": normalized_market,
        "status": final_status,
        "selected_provider": None,
        "persisted_article_count": 0,
        "persisted_sentiment_count": 0,
        "attempts": attempts,
        "diagnostics": diagnostics,
        "news": stored_news,
    }


def _refresh_from_adapter(
    adapter: NewsSearchAdapter,
    *,
    provider: str,
    symbol: str,
    max_results: int,
    session: Session,
) -> dict[str, object]:
    try:
        raw_candidates = adapter.search(
            symbol=symbol,
            query=_default_news_query(symbol),
            max_results=max_results,
        )
    except NewsSearchProviderTimeout:
        return {
            "status": "timeout",
            "attempt": {"provider": provider, "status": "timeout"},
            "diagnostic": _refresh_diagnostic(
                provider, "timeout", "warning", "PROVIDER_TIMEOUT"
            ),
        }
    except Exception:
        return {
            "status": "error",
            "attempt": {"provider": provider, "status": "failed"},
            "diagnostic": _refresh_diagnostic(
                provider, "error", "warning", "PROVIDER_ERROR"
            ),
        }

    if not isinstance(raw_candidates, list):
        return {
            "status": "error",
            "attempt": {"provider": provider, "status": "failed"},
            "diagnostic": _refresh_diagnostic(
                provider, "error", "warning", "PROVIDER_ERROR"
            ),
        }
    candidates = _normalize_news_candidate_batch(
        raw_candidates[:max_results],
        requested_symbol=symbol,
        expected_provider=provider,
    )
    if candidates is None:
        return {
            "status": "error",
            "attempt": {"provider": provider, "status": "failed"},
            "diagnostic": _refresh_diagnostic(
                provider,
                "error",
                "warning",
                "PROVIDER_INVALID_CANDIDATE",
            ),
        }
    persistable_candidates = [
        candidate for candidate in candidates if _is_persistable_news_candidate(candidate)
    ]
    if not persistable_candidates:
        code = "NO_PERSISTABLE_CANDIDATES" if candidates else "EMPTY_RESPONSE"
        return {
            "status": "empty",
            "attempt": {
                "provider": provider,
                "status": "empty",
                "candidate_count": len(candidates),
            },
            "diagnostic": _refresh_diagnostic(provider, "empty", "info", code),
        }

    try:
        article_count, sentiment_count = persist_news_search_candidates(
            persistable_candidates,
            session=session,
            expected_symbol=symbol,
            expected_provider=provider,
        )
    except SQLAlchemyError:
        session.rollback()
        return {
            "status": "error",
            "attempt": {"provider": provider, "status": "failed"},
            "diagnostic": _refresh_diagnostic(
                provider,
                "error",
                "warning",
                "PERSISTENCE_ERROR",
            ),
        }
    if article_count <= 0:
        return {
            "status": "empty",
            "attempt": {
                "provider": provider,
                "status": "empty",
                "candidate_count": len(candidates),
            },
            "diagnostic": _refresh_diagnostic(
                provider, "empty", "info", "EMPTY_RESPONSE"
            ),
        }
    return {
        "status": "persisted",
        "article_count": article_count,
        "sentiment_count": sentiment_count,
        "attempt": {
            "provider": provider,
            "status": "persisted",
            "candidate_count": len(candidates),
        },
        "diagnostic": _refresh_diagnostic(
            provider,
            "persisted",
            "info",
            "PROVIDER_PERSISTED",
            details={"article_count": article_count},
        ),
    }


def _run_refresh_source(
    adapter: NewsSearchAdapter,
    *,
    provider: str,
    symbol: str,
    market: str,
    max_results: int,
    session: Session,
    attempts: list[dict[str, object]],
    diagnostics: list[dict[str, object]],
) -> tuple[dict[str, object] | None, bool]:
    outcome = _refresh_from_adapter(
        adapter,
        provider=provider,
        symbol=symbol,
        max_results=max_results,
        session=session,
    )
    attempts.append(outcome["attempt"])
    diagnostics.append(outcome["diagnostic"])
    if outcome["status"] == "persisted":
        return (
            _refresh_success_payload(
                symbol=symbol,
                market=market,
                provider=provider,
                article_count=int(outcome["article_count"]),
                sentiment_count=int(outcome["sentiment_count"]),
                attempts=attempts,
                diagnostics=diagnostics,
                session=session,
            ),
            False,
        )
    return None, outcome["status"] in {"error", "timeout"}


def _refresh_success_payload(
    *,
    symbol: str,
    market: str,
    provider: str,
    article_count: int,
    sentiment_count: int,
    attempts: list[dict[str, object]],
    diagnostics: list[dict[str, object]],
    session: Session,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "market": market,
        "status": "refreshed",
        "selected_provider": provider,
        "persisted_article_count": article_count,
        "persisted_sentiment_count": sentiment_count,
        "attempts": attempts,
        "diagnostics": diagnostics,
        "news": get_news_sentiment_payload(symbol, session=session, market=market),
    }


def _refresh_diagnostic(
    provider: str,
    status: str,
    severity: str,
    code: str,
    *,
    details: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "provider": provider,
        "status": status,
        "severity": severity,
        "code": code,
    }
    if details:
        payload["details"] = details
    return payload


def _is_exact_cn_stock(symbol: str, market: str) -> bool:
    return market == "CN" and len(symbol) == 6 and symbol.isdigit()


def _normalize_news_candidate_batch(
    candidates: list[object],
    *,
    requested_symbol: str | None = None,
    expected_provider: str | None = None,
) -> list[NewsSearchCandidate] | None:
    normalized: list[NewsSearchCandidate] = []
    for candidate in candidates:
        normalized_candidate = _normalize_news_search_candidate(
            candidate,
            requested_symbol=requested_symbol,
            expected_provider=expected_provider,
        )
        if normalized_candidate is None:
            return None
        normalized.append(normalized_candidate)
    return normalized


def _normalize_news_search_candidate(
    candidate: object,
    *,
    requested_symbol: str | None = None,
    expected_provider: str | None = None,
) -> NewsSearchCandidate | None:
    if not isinstance(candidate, NewsSearchCandidate):
        return None
    string_fields = (
        candidate.symbol,
        candidate.query,
        candidate.title,
        candidate.url,
        candidate.source,
        candidate.provider,
        candidate.result_kind,
    )
    if any(not isinstance(value, str) for value in string_fields):
        return None
    if candidate.summary is not None and not isinstance(candidate.summary, str):
        return None
    if candidate.published_at is not None and not isinstance(candidate.published_at, datetime):
        return None
    if not isinstance(candidate.retrieved_at, datetime):
        return None

    symbol = candidate.symbol.strip().upper()
    normalized_requested_symbol = (
        requested_symbol.strip().upper() if requested_symbol is not None else None
    )
    if normalized_requested_symbol is not None and symbol != normalized_requested_symbol:
        return None
    provider = candidate.provider.strip().lower()
    normalized_expected_provider = (
        expected_provider.strip().lower() if expected_provider is not None else None
    )
    if (
        not provider
        or normalized_expected_provider is not None
        and provider != normalized_expected_provider
    ):
        return None
    normalized_article = normalize_news_article_fields(
        symbol=symbol,
        title=candidate.title,
        url=candidate.url,
        source=candidate.source or candidate.provider,
        published_at=candidate.published_at or candidate.retrieved_at,
        summary=candidate.summary,
    )
    if normalized_article is None:
        return None
    return replace(
        candidate,
        symbol=normalized_article.symbol,
        query=candidate.query.strip(),
        title=normalized_article.title,
        url=normalized_article.url,
        source=normalized_article.source,
        summary=normalized_article.summary,
        provider=provider,
        result_kind=candidate.result_kind.strip().lower(),
    )


def persist_news_search_candidates(
    candidates: list[NewsSearchCandidate],
    *,
    session: Session,
    expected_symbol: str | None = None,
    expected_provider: str | None = None,
) -> tuple[int, int]:
    article_count = 0
    sentiment_count = 0
    validated_candidates = _normalize_news_candidate_batch(
        list(candidates),
        requested_symbol=expected_symbol,
        expected_provider=expected_provider,
    )
    if validated_candidates is None:
        return 0, 0

    persistable_candidates = []
    for candidate in _dedupe_candidates(validated_candidates):
        if not _is_persistable_news_candidate(candidate):
            continue
        normalized_article = normalize_news_article_fields(
            symbol=candidate.symbol,
            title=candidate.title,
            url=candidate.url,
            source=candidate.source or candidate.provider,
            published_at=candidate.published_at or candidate.retrieved_at,
            summary=candidate.summary,
        )
        if normalized_article is None:
            return 0, 0
        persistable_candidates.append((candidate, normalized_article))

    for candidate, normalized_article in persistable_candidates:
        if persist_normalized_news_article(
            normalized_article,
            session=session,
            sentiment_reason=(
                f"Keyword sentiment classifier on {candidate.provider} "
                "search candidate"
            ),
        ):
            article_count += 1
            sentiment_count += 1

    session.commit()
    return article_count, sentiment_count


def _build_adapter(
    provider: str,
    *,
    api_key: str,
    timeout: float,
) -> NewsSearchAdapter:
    if provider == "anspire":
        return AnspireNewsSearchAdapter(api_key=api_key, timeout=timeout)
    if provider == "serpapi_baidu":
        return SerpApiBaiduNewsSearchAdapter(api_key=api_key, timeout=timeout)
    raise NewsSearchProviderError(f"Provider {provider} does not have a live adapter.")


def _request_json_payload(
    *,
    provider: str,
    url: str,
    http_getter: HttpGetter,
    timeout: float,
    params: Mapping[str, object],
    headers: Mapping[str, str] | None = None,
) -> object:
    try:
        response = http_getter(url, params=params, headers=headers, timeout=timeout)
        if isinstance(response, (Mapping, list)):
            return response
        raise_for_status = getattr(response, "raise_for_status", None)
        if callable(raise_for_status):
            raise_for_status()
        return response.json()
    except NewsSearchProviderError:
        raise
    except Exception as error:
        if _is_timeout_error(error):
            raise NewsSearchProviderTimeout(
                f"{provider} request timed out."
            ) from error
        raise NewsSearchProviderError(
            f"{provider} request failed with {type(error).__name__}."
        ) from error


def _default_http_getter(url: str, **kwargs: object) -> object:
    import httpx

    return httpx.get(url, **kwargs)


def _default_akshare_news_fetcher(symbol: str) -> object:
    import akshare as ak

    return ak.stock_news_em(symbol=symbol)


def _default_yfinance_ticker_factory(symbol: str) -> object:
    import yfinance as yf

    return yf.Ticker(symbol)


def _extract_result_rows(payload: object) -> list[Mapping[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, Mapping)]
    if not isinstance(payload, Mapping):
        raise NewsSearchProviderError("Provider response was not a JSON object or list.")

    for key in ("results", "data", "items"):
        rows = payload.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, Mapping)]
        if isinstance(rows, Mapping):
            nested_rows = rows.get("results") or rows.get("items")
            if isinstance(nested_rows, list):
                return [row for row in nested_rows if isinstance(row, Mapping)]
    return []


def _extract_named_rows(
    payload: Mapping[str, Any],
    key: str,
    result_kind: str,
) -> list[tuple[Mapping[str, Any], str]]:
    rows = payload.get(key)
    if not isinstance(rows, list):
        return []
    return [(row, result_kind) for row in rows if isinstance(row, Mapping)]


def _normalize_generic_result_rows(
    rows: list[Mapping[str, Any]],
    *,
    symbol: str,
    query: str,
    provider: str,
    default_source: str,
    default_region: str | None,
    default_language: str | None,
    default_result_kind: str,
    max_results: int,
) -> list[NewsSearchCandidate]:
    candidates: list[NewsSearchCandidate] = []
    for row in rows[:max_results]:
        candidate = _normalize_search_row(
            row,
            symbol=symbol,
            query=query,
            provider=provider,
            default_source=default_source,
            default_region=default_region,
            default_language=default_language,
            default_result_kind=default_result_kind,
        )
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def _normalize_search_row(
    row: Mapping[str, Any],
    *,
    symbol: str,
    query: str,
    provider: str,
    default_source: str,
    default_region: str | None,
    default_language: str | None,
    default_result_kind: str,
) -> NewsSearchCandidate | None:
    title = _first_text(row, ("title", "Title", "name", "headline"))
    url = _first_text(row, ("url", "URL", "link", "href"))
    if title is None or url is None:
        return None

    summary = _first_text(row, ("summary", "snippet", "content", "Content", "description"))
    source = _first_text(row, ("source", "Source", "publisher", "site", "domain")) or default_source
    raw_published_at = _first_value(
        row,
        ("published_at", "publishedAt", "date", "Date", "time", "timestamp"),
    )
    result_kind = _first_text(row, ("result_kind", "type", "kind")) or default_result_kind
    language = _first_text(row, ("language", "lang")) or default_language
    region = _first_text(row, ("region", "country")) or default_region

    return NewsSearchCandidate(
        symbol=symbol,
        query=query,
        title=title,
        url=url,
        source=source,
        summary=summary,
        published_at=_parse_datetime(raw_published_at),
        retrieved_at=datetime.now(timezone.utc),
        provider=provider,
        language=language,
        region=region,
        score=_parse_score(_first_value(row, ("score", "Score", "position", "rank"))),
        result_kind=result_kind,
    )


def _candidate_from_payload(payload: dict[str, object]) -> NewsSearchCandidate:
    return NewsSearchCandidate(
        symbol=str(payload.get("symbol") or "").strip().upper(),
        query=str(payload.get("query") or "").strip(),
        title=str(payload.get("title") or "").strip(),
        url=str(payload.get("url") or "").strip(),
        source=str(payload.get("source") or "").strip(),
        summary=_optional_payload_string(payload.get("summary")),
        published_at=_parse_datetime(payload.get("published_at")),
        retrieved_at=_parse_datetime(payload.get("retrieved_at")) or datetime.now(timezone.utc),
        provider=str(payload.get("provider") or "").strip(),
        language=_optional_payload_string(payload.get("language")),
        region=_optional_payload_string(payload.get("region")),
        score=_parse_score(payload.get("score")),
        result_kind=str(payload.get("result_kind") or "news"),
    )


def _candidate_evidence_boundary(result_kind: str) -> dict[str, object]:
    normalized_result_kind = result_kind.strip().lower()
    is_social_candidate = normalized_result_kind in SOCIAL_SENTIMENT_RESULT_KINDS
    return {
        "is_live_search_candidate": True,
        "is_ai_citable": False,
        "can_persist_as_news": normalized_result_kind in PERSISTABLE_NEWS_RESULT_KINDS,
        "evidence_strength": "low_social_signal"
        if is_social_candidate
        else "collection_candidate",
        "citation_policy": (
            "Social/public-opinion candidates require separate review and are not "
            "stored as NewsArticle evidence in this slice."
            if is_social_candidate
            else "Live search candidates become citable only after reviewed local storage."
        ),
    }


def _is_persistable_news_candidate(candidate: NewsSearchCandidate) -> bool:
    return candidate.result_kind.strip().lower() in PERSISTABLE_NEWS_RESULT_KINDS


def _is_social_sentiment_candidate(candidate: NewsSearchCandidate) -> bool:
    return candidate.result_kind.strip().lower() in SOCIAL_SENTIMENT_RESULT_KINDS


def _dedupe_candidates(candidates: list[NewsSearchCandidate]) -> list[NewsSearchCandidate]:
    deduped: list[NewsSearchCandidate] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate.title or not candidate.url:
            continue
        dedupe_hash = make_dedupe_hash(candidate.title, candidate.url)
        if dedupe_hash in seen:
            continue
        seen.add(dedupe_hash)
        deduped.append(candidate)
    return deduped


def _database_fallback_payload(
    symbol: str,
    *,
    session: Session | None,
    diagnostics: list[NewsSearchDiagnostic],
    live_candidate_count: int,
) -> dict[str, object] | None:
    if live_candidate_count > 0 or session is None:
        return None

    payload = get_news_sentiment_payload(symbol, session=session)
    article_count = _news_article_count(payload)
    if article_count > 0:
        diagnostics.append(
            _diagnostic(
                "database",
                "fallback",
                "info",
                "DATABASE_FALLBACK_USED",
                "No live provider returned candidates; using stored local news.",
                details={"article_count": article_count},
            )
        )
        return payload

    diagnostics.append(
        _diagnostic(
            "database",
            "empty",
            "info",
            "DATABASE_FALLBACK_EMPTY",
            "No live provider returned candidates and no stored news was available.",
        )
    )
    return payload


def _search_status(
    candidates: list[NewsSearchCandidate],
    database_fallback: dict[str, object] | None,
) -> str:
    if candidates:
        return "ok"
    if database_fallback:
        summary = database_fallback.get("summary")
        if isinstance(summary, dict) and int(summary.get("article_count", 0)) > 0:
            return "database_fallback"
    return "no_data"


def _news_article_count(payload: dict[str, object]) -> int:
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        return 0
    try:
        return int(summary.get("article_count", 0))
    except (TypeError, ValueError):
        return 0


def _default_news_query(symbol: str) -> str:
    return f"{symbol} financial news"


def _diagnostic(
    provider: str,
    status: str,
    severity: str,
    code: str,
    message: str,
    *,
    details: dict[str, object] | None = None,
) -> NewsSearchDiagnostic:
    return NewsSearchDiagnostic(
        provider=provider,
        status=status,
        severity=severity,
        code=code,
        message=message,
        details=details or {},
    )


def _first_text(row: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    raw_value = _first_value(row, keys)
    if raw_value is None or isinstance(raw_value, (Mapping, list, tuple, set)):
        return None
    text = str(raw_value).strip()
    return text or None


def _first_value(row: Mapping[str, Any], keys: tuple[str, ...]) -> object:
    for key in keys:
        if key in row and row[key] is not None:
            return row[key]
    return None


def _nested_mapping_text(
    row: Mapping[str, Any],
    outer_keys: tuple[str, ...],
    inner_keys: tuple[str, ...],
) -> str | None:
    for outer_key in outer_keys:
        nested = row.get(outer_key)
        if isinstance(nested, Mapping):
            value = _first_text(nested, inner_keys)
            if value:
                return value
    return None


def _optional_payload_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _frame_text(value: object) -> str | None:
    if value is None or isinstance(value, (Mapping, list, tuple, set)):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none"}:
        return None
    return text


def _parse_cn_news_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
    return parsed


def _parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _ensure_timezone(value)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None

    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return _parse_datetime(int(text))

    normalized = text.replace("Z", "+00:00")
    try:
        return _ensure_timezone(datetime.fromisoformat(normalized))
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _parse_score(value: object) -> float | None:
    if value is None:
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score != score:
        return None
    return score


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _isoformat_datetime(value: datetime) -> str:
    return _ensure_timezone(value).isoformat()


def _isoformat_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _isoformat_datetime(value)


def _is_timeout_error(error: Exception) -> bool:
    return "timeout" in type(error).__name__.lower() or isinstance(error, TimeoutError)
