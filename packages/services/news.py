from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
import re
from urllib.parse import parse_qsl, urlsplit

from sqlalchemy.orm import Session

from packages.analytics.sentiment import classify_sentiment, make_dedupe_hash
from packages.domain.models import (
    NEWS_ARTICLE_SOURCE_MAX_LENGTH,
    NEWS_ARTICLE_SYMBOL_MAX_LENGTH,
    NEWS_ARTICLE_TITLE_MAX_LENGTH,
    NEWS_ARTICLE_URL_MAX_LENGTH,
    NewsArticle,
    SentimentSignal,
)
from packages.providers.cn_market_helpers import normalize_cn_symbol
from packages.providers.eastmoney_public_news import (
    EastmoneyPublicNewsProviderError,
    fetch_eastmoney_public_news,
)
from packages.providers.yfinance_helpers import map_symbol_to_ticker
from packages.services.news_provider_registry import (
    normalize_news_search_max_results,
    normalize_news_search_timeout_seconds,
)
from packages.services.platform_settings import get_platform_settings
from packages.shared.config import settings


NEWS_ARTICLE_SUMMARY_MAX_LENGTH = 1000
_IGNORED_SUMMARY_TAGS = frozenset({"noscript", "script", "style", "template"})
_SENSITIVE_URL_KEY_PARTS = frozenset(
    {
        "auth",
        "authentication",
        "authorization",
        "bearer",
        "cookie",
        "credential",
        "credentials",
        "key",
        "password",
        "secret",
        "session",
        "sig",
        "signature",
        "token",
    }
)
_SENSITIVE_URL_KEY_ALIASES = frozenset(
    {
        "accesstoken",
        "apikey",
        "authkey",
        "authtoken",
        "clientsecret",
        "sessionid",
    }
)
_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_URL_KEY_PART_SEPARATOR = re.compile(r"[^A-Za-z0-9]+")
_SENSITIVE_NEWS_TEXT = re.compile(
    r"(?i)(?:\bbearer\s+\S+|"
    r"\b(?:api[_-]?key|access[_-]?token|auth(?:entication|orization)?|"
    r"cookie|password|secret|token)\b[\"']?\s*[:=]\s*[\"']?\s*\S+)"
)


class _NewsSummaryTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        del attrs
        if tag.lower() in _IGNORED_SUMMARY_TAGS:
            self._ignored_depth += 1
        elif self._ignored_depth == 0:
            self._parts.append(" ")

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        del attrs
        if self._ignored_depth == 0 and tag.lower() not in _IGNORED_SUMMARY_TAGS:
            self._parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in _IGNORED_SUMMARY_TAGS:
            self._ignored_depth = max(0, self._ignored_depth - 1)
        elif self._ignored_depth == 0:
            self._parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth == 0:
            self._parts.append(data)

    def normalized_text(self) -> str:
        return " ".join("".join(self._parts).split())


@dataclass(frozen=True)
class NormalizedNewsArticleFields:
    symbol: str
    title: str
    url: str
    source: str
    published_at: datetime
    summary: str | None


@dataclass(frozen=True)
class MockNewsArticle:
    symbol: str
    title: str
    url: str
    source: str
    published_at: datetime
    summary: str


def _mock_news(symbol: str) -> list[MockNewsArticle]:
    fixtures = {
        "AAPL": [
            MockNewsArticle(
                symbol="AAPL",
                title="Apple reports strong growth in services revenue",
                url="https://example.com/aapl-services-growth",
                source="mock_news",
                published_at=datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
                summary="Apple reports strong growth and record services profit in the quarter.",
            )
        ]
    }
    return fixtures.get(symbol, [])


def _isoformat_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def normalize_news_article_fields(
    *,
    symbol: object,
    title: object,
    url: object,
    source: object,
    published_at: object,
    summary: object,
) -> NormalizedNewsArticleFields | None:
    if not all(isinstance(value, str) for value in (symbol, title, url, source)):
        return None
    if summary is not None and not isinstance(summary, str):
        return None
    if not isinstance(published_at, datetime):
        return None

    normalized_symbol = str(symbol).strip().upper()
    normalized_title = " ".join(str(title).split())
    normalized_source = " ".join(str(source).split())
    normalized_summary = _normalize_news_summary(summary)
    if (
        not normalized_symbol
        or len(normalized_symbol) > NEWS_ARTICLE_SYMBOL_MAX_LENGTH
        or not normalized_title
        or len(normalized_title) > NEWS_ARTICLE_TITLE_MAX_LENGTH
        or not normalized_source
        or len(normalized_source) > NEWS_ARTICLE_SOURCE_MAX_LENGTH
    ):
        return None
    if any(
        _contains_sensitive_news_text(value)
        for value in (normalized_title, normalized_source, normalized_summary)
        if value is not None
    ):
        return None

    normalized_url = str(url)
    if not _is_safe_public_news_url(normalized_url):
        return None
    return NormalizedNewsArticleFields(
        symbol=normalized_symbol,
        title=normalized_title,
        url=normalized_url,
        source=normalized_source,
        published_at=published_at,
        summary=normalized_summary,
    )


def persist_normalized_news_article(
    candidate: NormalizedNewsArticleFields,
    *,
    session: Session,
    sentiment_reason: str,
) -> bool:
    dedupe_hash = make_dedupe_hash(candidate.title, candidate.url)
    existing = (
        session.query(NewsArticle)
        .filter(NewsArticle.dedupe_hash == dedupe_hash)
        .one_or_none()
    )
    if existing is not None:
        return False

    article = NewsArticle(
        symbol=candidate.symbol,
        title=candidate.title,
        url=candidate.url,
        source=candidate.source,
        published_at=candidate.published_at,
        summary=candidate.summary,
        dedupe_hash=dedupe_hash,
    )
    session.add(article)
    session.flush()
    sentiment = classify_sentiment(
        f"{candidate.title} {candidate.summary or ''}"
    )
    session.add(
        SentimentSignal(
            article_id=article.id,
            symbol=candidate.symbol,
            sentiment=sentiment.sentiment,
            confidence=sentiment.confidence,
            reason=sentiment_reason,
        )
    )
    return True


def _normalize_news_summary(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    parser = _NewsSummaryTextParser()
    parser.feed(value)
    parser.close()
    normalized = parser.normalized_text()
    if not normalized:
        return None
    return normalized[:NEWS_ARTICLE_SUMMARY_MAX_LENGTH].rstrip()


def _contains_sensitive_news_text(value: str) -> bool:
    return _SENSITIVE_NEWS_TEXT.search(value) is not None


def _is_safe_public_news_url(value: str) -> bool:
    if value != value.strip() or len(value) > NEWS_ARTICLE_URL_MAX_LENGTH:
        return False
    if any(character in value for character in ("\r", "\n", "\t")):
        return False
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        username = parsed.username
        password = parsed.password
    except ValueError:
        return False
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.netloc
        or not hostname
        or username is not None
        or password is not None
    ):
        return False
    return not _url_contains_sensitive_parameters(parsed.query, parsed.fragment)


def _url_contains_sensitive_parameters(query: str, fragment: str) -> bool:
    components = [query, fragment]
    if "?" in fragment:
        components.append(fragment.split("?", 1)[1])
    return any(
        _is_sensitive_url_parameter_name(name)
        for component in components
        for name, _value in parse_qsl(component, keep_blank_values=True)
    )


def _is_sensitive_url_parameter_name(value: str) -> bool:
    separated = _CAMEL_CASE_BOUNDARY.sub("_", value)
    parts = [
        part.lower()
        for part in _URL_KEY_PART_SEPARATOR.split(separated)
        if part
    ]
    collapsed = "".join(parts)
    return (
        collapsed in _SENSITIVE_URL_KEY_ALIASES
        or any(part in _SENSITIVE_URL_KEY_PARTS for part in parts)
    )


def ingest_mock_news(symbol: str, session: Session) -> dict[str, object]:
    article_count = 0
    sentiment_count = 0

    for fixture in _mock_news(symbol):
        candidate = normalize_news_article_fields(
            symbol=fixture.symbol,
            title=fixture.title,
            url=fixture.url,
            source=fixture.source,
            published_at=fixture.published_at,
            summary=fixture.summary,
        )
        if candidate is None or not persist_normalized_news_article(
            candidate,
            session=session,
            sentiment_reason="MVP keyword sentiment classifier",
        ):
            continue
        article_count += 1
        sentiment_count += 1

    session.commit()
    return {
        "symbol": symbol,
        "status": "ingested",
        "article_count": article_count,
        "sentiment_count": sentiment_count,
    }


def ingest_news(
    symbol: str,
    session: Session,
    provider_name: str | None = None,
) -> dict[str, object]:
    provider = (provider_name or settings.market_data_provider).lower()
    if provider == "yfinance":
        return ingest_yfinance_news(symbol, session=session)
    if provider == "akshare":
        return ingest_akshare_news(symbol, session=session)
    if provider == "tushare":
        return ingest_tushare_news(symbol, session=session)
    return ingest_mock_news(symbol, session=session)


def ingest_yfinance_news(symbol: str, session: Session) -> dict[str, object]:
    import yfinance as yf

    article_count = 0
    sentiment_count = 0
    ticker = yf.Ticker(map_symbol_to_ticker(symbol))
    news_items = getattr(ticker, "news", None) or []

    for entry in news_items[:10]:
        raw_title = entry.get("title")
        raw_url = entry.get("link") or entry.get("url")
        if not isinstance(raw_title, str) or not isinstance(raw_url, str):
            continue
        title = raw_title.strip()
        url = raw_url.strip()
        if not title or not url:
            continue
        raw_ts = entry.get("providerPublishTime") or entry.get("published_at")
        if raw_ts:
            published_at = datetime.fromtimestamp(int(raw_ts), tz=timezone.utc)
        else:
            published_at = datetime.now(timezone.utc)
        candidate = normalize_news_article_fields(
            symbol=symbol.upper(),
            title=title,
            url=url,
            source=entry.get("publisher") or "yfinance",
            published_at=published_at,
            summary=entry.get("summary") or title,
        )
        if candidate is None or not persist_normalized_news_article(
            candidate,
            session=session,
            sentiment_reason="Keyword sentiment classifier on yfinance headline",
        ):
            continue
        article_count += 1
        sentiment_count += 1

    session.commit()
    return {
        "symbol": symbol,
        "status": "ingested",
        "source": "yfinance",
        "article_count": article_count,
        "sentiment_count": sentiment_count,
    }


def ingest_akshare_news(symbol: str, session: Session) -> dict[str, object]:
    code = normalize_cn_symbol(symbol)
    settings_payload = get_platform_settings()
    if not bool(settings_payload.get("akshare_enabled", False)):
        return {
            "symbol": symbol,
            "status": "skipped",
            "source": "eastmoney_public",
            "code": "PROVIDER_DISABLED",
            "article_count": 0,
            "sentiment_count": 0,
        }
    timeout = normalize_news_search_timeout_seconds(
        settings_payload.get("news_search_timeout_seconds")
    )
    max_rows = normalize_news_search_max_results(
        settings_payload.get("news_search_max_results")
    )
    try:
        items = fetch_eastmoney_public_news(
            code,
            timeout=timeout,
            max_rows=max_rows,
        )
    except EastmoneyPublicNewsProviderError as error:
        return {
            "symbol": symbol,
            "status": "provider_error",
            "source": "eastmoney_public",
            "code": error.code,
            "article_count": 0,
            "sentiment_count": 0,
        }

    article_count = 0
    sentiment_count = 0
    for item in items:
        candidate = normalize_news_article_fields(
            symbol=code,
            title=item.title,
            url=item.url,
            source=item.publisher,
            published_at=item.published_at,
            summary=item.summary or item.title,
        )
        if candidate is None or not persist_normalized_news_article(
            candidate,
            session=session,
            sentiment_reason="Keyword sentiment classifier on Eastmoney public headline",
        ):
            continue
        article_count += 1
        sentiment_count += 1

    session.commit()
    if article_count > 0:
        status = "ingested"
    elif items:
        status = "skipped"
    else:
        status = "empty"
    return {
        "symbol": symbol,
        "status": status,
        "source": "eastmoney_public",
        "article_count": article_count,
        "sentiment_count": sentiment_count,
    }


def ingest_tushare_news(symbol: str, session: Session) -> dict[str, object]:
    from packages.services.platform_settings import get_platform_settings

    token = str(get_platform_settings().get("tushare_token", "") or "").strip()
    if not token:
        return {"symbol": symbol, "status": "skipped", "source": "tushare", "reason": "missing token"}

    return {
        "symbol": symbol,
        "status": "empty",
        "source": "tushare",
        "article_count": 0,
        "sentiment_count": 0,
    }


def is_supported_news_identity(symbol: str, market: str) -> bool:
    normalized_symbol = symbol.strip().upper()
    normalized_market = market.strip().upper()
    if normalized_market == "CN":
        return len(normalized_symbol) == 6 and normalized_symbol.isdigit()
    if normalized_market == "HK":
        return 1 <= len(normalized_symbol) <= 5 and normalized_symbol.isdigit()
    if normalized_market == "US":
        return bool(re.fullmatch(r"[A-Z][A-Z0-9.-]{0,63}", normalized_symbol))
    return False


def build_empty_news_sentiment_payload(symbol: str) -> dict[str, object]:
    return {
        "symbol": symbol.strip().upper(),
        "source": "database",
        "summary": {"latest_sentiment": None, "article_count": 0},
        "items": [],
    }


def get_news_sentiment_payload(
    symbol: str,
    session: Session,
    *,
    market: str | None = None,
) -> dict[str, object]:
    normalized_symbol = symbol.strip().upper()
    if market is not None and not is_supported_news_identity(normalized_symbol, market):
        return build_empty_news_sentiment_payload(normalized_symbol)
    rows = (
        session.query(NewsArticle, SentimentSignal)
        .outerjoin(SentimentSignal, SentimentSignal.article_id == NewsArticle.id)
        .filter(NewsArticle.symbol == normalized_symbol)
        .order_by(NewsArticle.published_at.desc())
        .all()
    )
    items = [
        {
            "title": article.title,
            "url": article.url,
            "source": article.source,
            "published_at": _isoformat_utc(article.published_at),
            "summary": article.summary,
            "sentiment": signal.sentiment if signal is not None else None,
            "confidence": float(signal.confidence) if signal is not None else None,
        }
        for article, signal in rows
    ]
    latest_sentiment = next(
        (item["sentiment"] for item in items if item["sentiment"] is not None),
        None,
    )

    return {
        "symbol": normalized_symbol,
        "source": "database",
        "summary": {
            "latest_sentiment": latest_sentiment,
            "article_count": len(items),
        },
        "items": items,
    }


def get_latest_news_payload(
    session: Session,
    *,
    limit: int = 10,
) -> dict[str, object]:
    bounded_limit = max(1, min(int(limit), 50))
    rows = (
        session.query(NewsArticle, SentimentSignal)
        .outerjoin(SentimentSignal, SentimentSignal.article_id == NewsArticle.id)
        .order_by(NewsArticle.published_at.desc(), NewsArticle.id.desc())
        .limit(bounded_limit)
        .all()
    )
    items = [
        {
            "symbol": article.symbol,
            "title": article.title,
            "url": article.url,
            "source": article.source,
            "published_at": _isoformat_utc(article.published_at),
            "summary": article.summary,
            "sentiment": signal.sentiment if signal is not None else None,
            "confidence": float(signal.confidence) if signal is not None else None,
        }
        for article, signal in rows
    ]
    return {
        "source": "database",
        "status": "ok" if items else "no_data",
        "limit": bounded_limit,
        "count": len(items),
        "items": items,
    }
