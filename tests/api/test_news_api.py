from datetime import datetime, timezone

import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.services.news_search import NewsSearchCandidate, persist_news_search_candidates
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


def test_news_read_uses_optional_exact_market_identity():
    session = make_session()
    persist_news_search_candidates(
        [
            NewsSearchCandidate(
                symbol="000001",
                query="000001 financial news",
                title="Ping An Bank publishes an update",
                url="https://example.com/pab-market-read",
                source="Example Finance",
                summary="A stored CN article.",
                published_at=datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc),
                retrieved_at=datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc),
                provider="akshare",
            )
        ],
        session=session,
    )

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        cn_response = client.get("/news/000001", params={"market": "CN"})
        wrong_market_response = client.get("/news/000001", params={"market": "US"})
    finally:
        app.dependency_overrides.clear()

    assert cn_response.status_code == 200
    assert cn_response.json()["summary"]["article_count"] == 1
    assert wrong_market_response.status_code == 200
    assert wrong_market_response.json()["summary"]["article_count"] == 0


def test_get_news_stays_read_only_when_stored_news_is_empty(monkeypatch):
    session = make_session()

    def unexpected_source_call(*args, **kwargs):
        raise AssertionError("GET /news/{symbol} must not call external providers")

    monkeypatch.setattr(
        "packages.services.news_search._default_akshare_news_fetcher",
        unexpected_source_call,
    )
    monkeypatch.setattr(
        "packages.services.news_search._default_yfinance_ticker_factory",
        unexpected_source_call,
    )

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        response = TestClient(app).get("/news/000001")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["summary"]["article_count"] == 0


def test_news_refresh_returns_stored_news_before_external_fallbacks():
    session = make_session()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        client.post("/news/mock-ingest", params={"symbol": "AAPL"})
        refresh_response = client.post(
            "/news/AAPL/refresh",
            params={"market": "US"},
        )
    finally:
        app.dependency_overrides.clear()

    assert refresh_response.status_code == 200
    payload = refresh_response.json()
    assert payload["status"] == "database_hit"
    assert payload["selected_provider"] == "database"
    assert payload["persisted_article_count"] == 0
    assert payload["attempts"] == []
    assert payload["news"]["summary"]["article_count"] == 1
    assert payload["diagnostics"] == [
        {
            "provider": "database",
            "status": "ok",
            "severity": "info",
            "code": "DATABASE_HIT",
            "details": {"article_count": 1},
        }
    ]


def test_latest_news_api_returns_bounded_cross_symbol_stored_rows():
    session = make_session()
    persist_news_search_candidates(
        [
            NewsSearchCandidate(
                symbol="AAPL",
                query="AAPL financial news",
                title="Apple services update",
                url="https://example.com/apple-update",
                source="Example Finance",
                summary="Apple services update.",
                published_at=datetime(2026, 7, 14, 8, 0, tzinfo=timezone.utc),
                retrieved_at=datetime(2026, 7, 14, 9, 0, tzinfo=timezone.utc),
                provider="anspire",
            ),
            NewsSearchCandidate(
                symbol="600519",
                query="600519 financial news",
                title="Moutai operating update",
                url="https://example.com/moutai-update",
                source="Example Finance",
                summary="Moutai operating update.",
                published_at=datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc),
                retrieved_at=datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc),
                provider="anspire",
            ),
        ],
        session=session,
    )

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        response = TestClient(app).get("/news/latest", params={"limit": 1})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "database"
    assert payload["status"] == "ok"
    assert payload["limit"] == 1
    assert payload["count"] == 1
    assert payload["items"][0]["symbol"] == "600519"
    assert payload["items"][0]["title"] == "Moutai operating update"


def test_latest_news_api_distinguishes_an_empty_store():
    session = make_session()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        response = TestClient(app).get("/news/latest", params={"limit": 6})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "source": "database",
        "status": "no_data",
        "limit": 6,
        "count": 0,
        "items": [],
    }


def test_news_refresh_api_persists_first_builtin_cn_source(monkeypatch):
    session = make_session()
    monkeypatch.setattr(
        "packages.services.news_search.get_platform_settings",
        lambda: {
            "news_search_provider_order": ["anspire", "serpapi_baidu"],
            "news_search_enabled_providers": ["anspire", "serpapi_baidu"],
            "news_search_provider_keys": {},
            "news_search_max_results": 5,
            "news_search_timeout_seconds": 3,
            "akshare_enabled": True,
        },
    )
    monkeypatch.setattr(
        "packages.services.news_search._default_akshare_news_fetcher",
        lambda symbol: pd.DataFrame(
            [
                {
                    "新闻标题": "Ping An Bank publishes operating update",
                    "新闻链接": "https://example.com/pab-api-update",
                    "发布时间": "2026-07-15 14:30:00",
                    "文章来源": "eastmoney",
                    "新闻内容": "Ping An Bank published an operating update.",
                }
            ]
        ),
    )

    def unexpected_yfinance_factory(symbol: str):
        raise AssertionError("yfinance must not run after AkShare persisted success")

    monkeypatch.setattr(
        "packages.services.news_search._default_yfinance_ticker_factory",
        unexpected_yfinance_factory,
    )

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        refresh_response = client.post(
            "/news/000001/refresh",
            params={"market": "CN"},
        )
        stored_response = client.get("/news/000001")
    finally:
        app.dependency_overrides.clear()

    assert refresh_response.status_code == 200
    refresh_payload = refresh_response.json()
    assert refresh_payload["status"] == "refreshed"
    assert refresh_payload["selected_provider"] == "akshare"
    assert refresh_payload["persisted_article_count"] == 1
    assert stored_response.status_code == 200
    assert stored_response.json()["summary"]["article_count"] == 1


def test_news_search_api_uses_database_fallback_without_provider_keys(monkeypatch):
    session = make_session()

    def override_session():
        yield session

    monkeypatch.setattr(
        "packages.services.news_search.get_platform_settings",
        lambda: {
            "news_search_provider_order": ["anspire"],
            "news_search_enabled_providers": ["anspire"],
            "news_search_provider_keys": {},
            "news_search_max_results": 5,
            "news_search_timeout_seconds": 3,
        },
    )

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        client.post("/news/mock-ingest", params={"symbol": "AAPL"})
        search_response = client.get("/news/search", params={"symbol": "AAPL"})
    finally:
        app.dependency_overrides.clear()

    assert search_response.status_code == 200
    payload = search_response.json()
    codes = [diagnostic["code"] for diagnostic in payload["diagnostics"]]
    assert payload["status"] == "database_fallback"
    assert payload["database_fallback"]["summary"]["article_count"] == 1
    assert "MISSING_CREDENTIALS" in codes
    assert "DATABASE_FALLBACK_USED" in codes
