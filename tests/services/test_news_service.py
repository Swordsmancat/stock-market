from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.services.news import get_news_sentiment_payload, ingest_mock_news
from packages.shared.database import Base


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_ingests_mock_news_dedupes_and_stores_sentiment():
    session = make_session()

    first_result = ingest_mock_news("AAPL", session=session)
    second_result = ingest_mock_news("AAPL", session=session)
    payload = get_news_sentiment_payload("AAPL", session=session)

    assert first_result["status"] == "ingested"
    assert first_result["article_count"] == 1
    assert first_result["sentiment_count"] == 1
    assert second_result["article_count"] == 0
    assert second_result["sentiment_count"] == 0

    assert payload["symbol"] == "AAPL"
    assert payload["source"] == "database"
    assert payload["summary"]["latest_sentiment"] == "positive"
    assert payload["summary"]["article_count"] == 1
    assert payload["items"][0]["title"] == "Apple reports strong growth in services revenue"
    assert payload["items"][0]["sentiment"] == "positive"
    assert payload["items"][0]["confidence"] == 0.6
