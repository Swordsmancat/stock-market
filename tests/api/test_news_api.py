from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.shared.database import Base, get_session


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_news_api_ingests_and_reads_database_sentiment():
    session = make_session()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        ingest_response = client.post("/news/mock-ingest", params={"symbol": "AAPL"})
        news_response = client.get("/news/AAPL")
    finally:
        app.dependency_overrides.clear()

    assert ingest_response.status_code == 200
    ingest_payload = ingest_response.json()
    assert ingest_payload["status"] == "ingested"
    assert ingest_payload["article_count"] == 1
    assert ingest_payload["sentiment_count"] == 1

    assert news_response.status_code == 200
    news_payload = news_response.json()
    assert news_payload["symbol"] == "AAPL"
    assert news_payload["source"] == "database"
    assert news_payload["summary"]["latest_sentiment"] == "positive"
    assert news_payload["summary"]["article_count"] == 1
    assert news_payload["items"][0]["title"] == "Apple reports strong growth in services revenue"
    assert news_payload["items"][0]["sentiment"] == "positive"
    assert news_payload["items"][0]["confidence"] == 0.6
