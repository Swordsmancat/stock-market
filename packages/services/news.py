from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from packages.analytics.sentiment import classify_sentiment, make_dedupe_hash
from packages.domain.models import NewsArticle, SentimentSignal
from packages.providers.cn_market_helpers import (
    find_column,
    normalize_cn_symbol,
    parse_cn_datetime,
    tushare_ts_code,
)
from packages.providers.yfinance_helpers import map_symbol_to_ticker
from packages.shared.config import settings


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


def ingest_mock_news(symbol: str, session: Session) -> dict[str, object]:
    article_count = 0
    sentiment_count = 0

    for fixture in _mock_news(symbol):
        dedupe_hash = make_dedupe_hash(fixture.title, fixture.url)
        existing = (
            session.query(NewsArticle)
            .filter(NewsArticle.dedupe_hash == dedupe_hash)
            .one_or_none()
        )
        if existing is not None:
            continue

        article = NewsArticle(
            symbol=fixture.symbol,
            title=fixture.title,
            url=fixture.url,
            source=fixture.source,
            published_at=fixture.published_at,
            summary=fixture.summary,
            dedupe_hash=dedupe_hash,
        )
        session.add(article)
        session.flush()

        sentiment = classify_sentiment(f"{fixture.title} {fixture.summary}")
        session.add(
            SentimentSignal(
                article_id=article.id,
                symbol=fixture.symbol,
                sentiment=sentiment.sentiment,
                confidence=sentiment.confidence,
                reason="MVP keyword sentiment classifier",
            )
        )
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
        title = str(entry.get("title") or "").strip()
        url = str(entry.get("link") or entry.get("url") or "").strip()
        if not title or not url:
            continue
        raw_ts = entry.get("providerPublishTime") or entry.get("published_at")
        if raw_ts:
            published_at = datetime.fromtimestamp(int(raw_ts), tz=timezone.utc)
        else:
            published_at = datetime.now(timezone.utc)
        summary = str(entry.get("summary") or title)
        dedupe_hash = make_dedupe_hash(title, url)
        existing = (
            session.query(NewsArticle)
            .filter(NewsArticle.dedupe_hash == dedupe_hash)
            .one_or_none()
        )
        if existing is not None:
            continue

        article = NewsArticle(
            symbol=symbol.upper(),
            title=title,
            url=url,
            source=str(entry.get("publisher") or "yfinance"),
            published_at=published_at,
            summary=summary,
            dedupe_hash=dedupe_hash,
        )
        session.add(article)
        session.flush()

        sentiment = classify_sentiment(f"{title} {summary}")
        session.add(
            SentimentSignal(
                article_id=article.id,
                symbol=symbol.upper(),
                sentiment=sentiment.sentiment,
                confidence=sentiment.confidence,
                reason="Keyword sentiment classifier on yfinance headline",
            )
        )
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
    try:
        import akshare as ak
    except ImportError:
        return {"symbol": symbol, "status": "skipped", "source": "akshare", "reason": "akshare not installed"}

    code = normalize_cn_symbol(symbol)
    try:
        df = ak.stock_news_em(symbol=code)
    except Exception:
        return {"symbol": symbol, "status": "empty", "source": "akshare", "article_count": 0, "sentiment_count": 0}

    if df is None or df.empty:
        return {"symbol": symbol, "status": "empty", "source": "akshare", "article_count": 0, "sentiment_count": 0}

    columns = [str(column) for column in df.columns]
    title_col = find_column(columns, "新闻标题") or find_column(columns, "标题")
    url_col = find_column(columns, "新闻链接") or find_column(columns, "链接")
    published_col = find_column(columns, "发布时间")
    source_col = find_column(columns, "文章来源") or find_column(columns, "来源")
    summary_col = find_column(columns, "新闻内容") or find_column(columns, "内容")

    article_count = 0
    sentiment_count = 0
    for _, entry in df.head(10).iterrows():
        title = str(entry[title_col]).strip() if title_col else ""
        url = str(entry[url_col]).strip() if url_col else ""
        if not title or not url:
            continue
        published_at = parse_cn_datetime(entry[published_col]) if published_col else datetime.now(timezone.utc)
        summary = str(entry[summary_col]).strip() if summary_col else title
        source = str(entry[source_col]).strip() if source_col else "akshare"

        dedupe_hash = make_dedupe_hash(title, url)
        existing = (
            session.query(NewsArticle)
            .filter(NewsArticle.dedupe_hash == dedupe_hash)
            .one_or_none()
        )
        if existing is not None:
            continue

        article = NewsArticle(
            symbol=code,
            title=title,
            url=url,
            source=source,
            published_at=published_at,
            summary=summary,
            dedupe_hash=dedupe_hash,
        )
        session.add(article)
        session.flush()

        sentiment = classify_sentiment(f"{title} {summary}")
        session.add(
            SentimentSignal(
                article_id=article.id,
                symbol=code,
                sentiment=sentiment.sentiment,
                confidence=sentiment.confidence,
                reason="Keyword sentiment classifier on akshare headline",
            )
        )
        article_count += 1
        sentiment_count += 1

    session.commit()
    return {
        "symbol": symbol,
        "status": "ingested",
        "source": "akshare",
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


def get_news_sentiment_payload(symbol: str, session: Session) -> dict[str, object]:
    rows = (
        session.query(NewsArticle, SentimentSignal)
        .join(SentimentSignal, SentimentSignal.article_id == NewsArticle.id)
        .filter(NewsArticle.symbol == symbol)
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
            "sentiment": signal.sentiment,
            "confidence": float(signal.confidence),
        }
        for article, signal in rows
    ]
    latest_sentiment = items[0]["sentiment"] if items else "neutral"

    return {
        "symbol": symbol,
        "source": "database",
        "summary": {
            "latest_sentiment": latest_sentiment,
            "article_count": len(items),
        },
        "items": items,
    }
