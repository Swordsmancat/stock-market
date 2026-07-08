from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from sqlalchemy.orm import Session

from packages.analytics.sentiment import classify_sentiment, make_dedupe_hash
from packages.domain.models import NewsArticle, SentimentSignal
from packages.services.news import get_news_sentiment_payload
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
    article_count, sentiment_count = persist_news_search_candidates(candidates, session=session)
    return {
        **payload,
        "status": "ingested" if article_count > 0 else payload["status"],
        "article_count": article_count,
        "sentiment_count": sentiment_count,
        "social_candidate_count": social_candidate_count,
        "social_candidates_deferred": social_candidate_count > 0,
    }


def persist_news_search_candidates(
    candidates: list[NewsSearchCandidate],
    *,
    session: Session,
) -> tuple[int, int]:
    article_count = 0
    sentiment_count = 0
    for candidate in _dedupe_candidates(candidates):
        if not _is_persistable_news_candidate(candidate):
            continue

        dedupe_hash = make_dedupe_hash(candidate.title, candidate.url)
        existing = (
            session.query(NewsArticle)
            .filter(NewsArticle.dedupe_hash == dedupe_hash)
            .one_or_none()
        )
        if existing is not None:
            continue

        article = NewsArticle(
            symbol=candidate.symbol,
            title=candidate.title,
            url=candidate.url,
            source=candidate.source or candidate.provider,
            published_at=candidate.published_at or candidate.retrieved_at,
            summary=candidate.summary,
            dedupe_hash=dedupe_hash,
        )
        session.add(article)
        session.flush()

        sentiment = classify_sentiment(f"{candidate.title} {candidate.summary or ''}")
        session.add(
            SentimentSignal(
                article_id=article.id,
                symbol=candidate.symbol,
                sentiment=sentiment.sentiment,
                confidence=sentiment.confidence,
                reason=f"Keyword sentiment classifier on {candidate.provider} search candidate",
            )
        )
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
    article_count = int(payload.get("summary", {}).get("article_count", 0))  # type: ignore[union-attr]
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
    if raw_value is None:
        return None
    text = str(raw_value).strip()
    return text or None


def _first_value(row: Mapping[str, Any], keys: tuple[str, ...]) -> object:
    for key in keys:
        if key in row and row[key] is not None:
            return row[key]
    return None


def _optional_payload_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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
