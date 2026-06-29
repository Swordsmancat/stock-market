from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from packages.analytics.sentiment import classify_sentiment, make_dedupe_hash
from packages.domain.models import NewsArticle, SentimentSignal


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
