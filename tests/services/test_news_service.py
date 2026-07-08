from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.services.news import get_news_sentiment_payload, ingest_mock_news
from packages.services.news_search import (
    AnspireNewsSearchAdapter,
    NewsSearchCandidate,
    NewsSearchProviderTimeout,
    SerpApiBaiduNewsSearchAdapter,
    search_and_ingest_news_candidates,
    search_news_candidates,
)
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


def test_anspire_adapter_normalizes_results_without_exposing_key():
    calls = {}

    def fake_getter(url, **kwargs):
        calls["url"] = url
        calls["headers"] = kwargs["headers"]
        calls["params"] = kwargs["params"]
        return {
            "results": [
                {
                    "title": "AAPL services profit grows",
                    "url": "https://example.com/aapl-services",
                    "content": "Apple services profit grows strongly.",
                    "score": 0.91,
                    "date": "2026-07-08T09:30:00+00:00",
                }
            ]
        }

    adapter = AnspireNewsSearchAdapter(api_key="secret-key", http_getter=fake_getter)

    candidates = adapter.search(symbol="AAPL", query="AAPL financial news", max_results=5)

    assert calls["headers"]["Authorization"] == "Bearer secret-key"
    assert calls["params"] == {"query": "AAPL financial news", "top_k": 5}
    assert candidates[0].provider == "anspire"
    assert candidates[0].title == "AAPL services profit grows"
    assert candidates[0].source == "Anspire AI Search"
    assert candidates[0].published_at == datetime(2026, 7, 8, 9, 30, tzinfo=timezone.utc)
    assert "secret-key" not in str(candidates[0].to_payload())


def test_serpapi_baidu_adapter_normalizes_news_and_web_results():
    def fake_getter(url, **kwargs):
        return {
            "news_results": [
                {
                    "title": "茅台新闻",
                    "link": "https://example.com/moutai-news",
                    "snippet": "茅台业绩增长。",
                    "source": "财联社",
                    "date": "2026-07-08",
                }
            ],
            "organic_results": [
                {
                    "title": "Moutai company page",
                    "link": "https://example.com/moutai",
                    "snippet": "Company profile.",
                    "source": "Baidu",
                    "position": 2,
                }
            ],
        }

    adapter = SerpApiBaiduNewsSearchAdapter(api_key="serp-secret", http_getter=fake_getter)

    candidates = adapter.search(symbol="600519", query="600519 新闻", max_results=10)

    assert [candidate.result_kind for candidate in candidates] == ["news", "web"]
    assert candidates[0].provider == "serpapi_baidu"
    assert candidates[0].language == "zh"
    assert candidates[0].region == "CN"
    assert candidates[0].source == "财联社"
    assert candidates[1].score == 2.0


def test_search_news_records_timeout_empty_and_success_diagnostics():
    class TimeoutAdapter:
        provider = "anspire"

        def search(self, **kwargs):
            raise NewsSearchProviderTimeout("timeout")

    class EmptyAdapter:
        provider = "serpapi_baidu"

        def search(self, **kwargs):
            return []

    payload = search_news_candidates(
        "AAPL",
        settings_payload={
            "news_search_provider_order": ["anspire", "serpapi_baidu", "tavily"],
            "news_search_enabled_providers": ["anspire", "serpapi_baidu", "tavily"],
            "news_search_provider_keys": {
                "anspire": "secret",
                "serpapi_baidu": "secret",
                "tavily": "secret",
            },
            "news_search_max_results": 5,
            "news_search_timeout_seconds": 3,
        },
        adapters={"anspire": TimeoutAdapter(), "serpapi_baidu": EmptyAdapter()},
    )

    codes = [diagnostic["code"] for diagnostic in payload["diagnostics"]]
    assert payload["status"] == "no_data"
    assert "PROVIDER_TIMEOUT" in codes
    assert "EMPTY_RESPONSE" in codes
    assert "PROVIDER_NOT_IMPLEMENTED" in codes


def test_search_news_falls_back_to_database_when_live_providers_are_unavailable():
    session = make_session()
    ingest_mock_news("AAPL", session=session)

    payload = search_news_candidates(
        "AAPL",
        session=session,
        settings_payload={
            "news_search_provider_order": ["anspire"],
            "news_search_enabled_providers": ["anspire"],
            "news_search_provider_keys": {},
            "news_search_max_results": 5,
            "news_search_timeout_seconds": 3,
        },
    )

    codes = [diagnostic["code"] for diagnostic in payload["diagnostics"]]
    assert payload["status"] == "database_fallback"
    assert payload["candidate_count"] == 0
    assert payload["database_fallback"]["summary"]["article_count"] == 1
    assert "MISSING_CREDENTIALS" in codes
    assert "DATABASE_FALLBACK_USED" in codes


def test_search_and_ingest_news_candidates_dedupes_and_stores_sentiment():
    session = make_session()
    retrieved_at = datetime(2026, 7, 8, 10, 0, tzinfo=timezone.utc)
    candidate = NewsSearchCandidate(
        symbol="AAPL",
        query="AAPL financial news",
        title="Apple profit grows",
        url="https://example.com/apple-profit",
        source="Example Finance",
        summary="Apple reports strong profit growth.",
        published_at=None,
        retrieved_at=retrieved_at,
        provider="anspire",
        score=0.8,
    )

    class DuplicateAdapter:
        provider = "anspire"

        def search(self, **kwargs):
            return [candidate, candidate]

    first_result = search_and_ingest_news_candidates(
        "AAPL",
        session=session,
        settings_payload={
            "news_search_provider_order": ["anspire"],
            "news_search_enabled_providers": ["anspire"],
            "news_search_provider_keys": {"anspire": "secret"},
            "news_search_max_results": 5,
            "news_search_timeout_seconds": 3,
        },
        adapters={"anspire": DuplicateAdapter()},
    )
    second_result = search_and_ingest_news_candidates(
        "AAPL",
        session=session,
        settings_payload={
            "news_search_provider_order": ["anspire"],
            "news_search_enabled_providers": ["anspire"],
            "news_search_provider_keys": {"anspire": "secret"},
            "news_search_max_results": 5,
            "news_search_timeout_seconds": 3,
        },
        adapters={"anspire": DuplicateAdapter()},
    )
    payload = get_news_sentiment_payload("AAPL", session=session)

    assert first_result["article_count"] == 1
    assert first_result["sentiment_count"] == 1
    assert second_result["article_count"] == 0
    assert payload["summary"]["article_count"] == 1
    assert payload["items"][0]["source"] == "Example Finance"
    assert payload["items"][0]["sentiment"] == "positive"


def test_search_ingest_defers_social_candidates_from_stored_news():
    session = make_session()
    retrieved_at = datetime(2026, 7, 8, 10, 0, tzinfo=timezone.utc)
    news_candidate = NewsSearchCandidate(
        symbol="AAPL",
        query="AAPL financial news",
        title="Apple profit grows",
        url="https://example.com/apple-profit",
        source="Example Finance",
        summary="Apple reports strong profit growth.",
        published_at=None,
        retrieved_at=retrieved_at,
        provider="serpapi_baidu",
        result_kind="news",
    )
    social_candidate = NewsSearchCandidate(
        symbol="AAPL",
        query="AAPL financial news",
        title="Apple mentioned heavily on social media",
        url="https://example.com/apple-social",
        source="Example Social",
        summary="Social posts discuss Apple momentum.",
        published_at=None,
        retrieved_at=retrieved_at,
        provider="serpapi_baidu",
        result_kind="social",
    )

    class MixedAdapter:
        provider = "serpapi_baidu"

        def search(self, **kwargs):
            return [news_candidate, social_candidate]

    result = search_and_ingest_news_candidates(
        "AAPL",
        session=session,
        settings_payload={
            "news_search_provider_order": ["serpapi_baidu"],
            "news_search_enabled_providers": ["serpapi_baidu"],
            "news_search_provider_keys": {"serpapi_baidu": "secret"},
            "news_search_max_results": 5,
            "news_search_timeout_seconds": 3,
        },
        adapters={"serpapi_baidu": MixedAdapter()},
    )
    payload = get_news_sentiment_payload("AAPL", session=session)
    social_payload = next(
        candidate for candidate in result["candidates"] if candidate["result_kind"] == "social"
    )

    assert result["article_count"] == 1
    assert result["sentiment_count"] == 1
    assert result["social_candidate_count"] == 1
    assert result["social_candidates_deferred"] is True
    assert result["safety"]["social_sentiment_separated"] is True
    assert payload["summary"]["article_count"] == 1
    assert payload["items"][0]["title"] == "Apple profit grows"
    assert social_payload["evidence_boundary"] == {
        "is_live_search_candidate": True,
        "is_ai_citable": False,
        "can_persist_as_news": False,
        "evidence_strength": "low_social_signal",
        "citation_policy": (
            "Social/public-opinion candidates require separate review and are not "
            "stored as NewsArticle evidence in this slice."
        ),
    }
