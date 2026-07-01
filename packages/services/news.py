from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from packages.analytics.sentiment import classify_sentiment, make_dedupe_hash
from packages.domain.models import NewsArticle, SentimentSignal
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
