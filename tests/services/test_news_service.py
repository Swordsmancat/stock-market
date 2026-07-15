from datetime import datetime, timezone

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import NewsArticle
from packages.services.news import (
    get_news_sentiment_payload,
    ingest_akshare_news,
    ingest_mock_news,
    ingest_yfinance_news,
)
from packages.services.news_search import (
    AkShareNewsSearchAdapter,
    AnspireNewsSearchAdapter,
    NewsSearchCandidate,
    NewsSearchProviderTimeout,
    SerpApiBaiduNewsSearchAdapter,
    YFinanceNewsSearchAdapter,
    persist_news_search_candidates,
    refresh_news_candidates,
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


def test_get_news_keeps_stored_articles_without_sentiment_rows():
    session = make_session()
    session.add(
        NewsArticle(
            symbol="600519",
            title="Moutai publishes a company update",
            url="https://example.com/moutai-company-update",
            source="Example Finance",
            published_at=datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc),
            summary="A stored article without a sentiment projection.",
            dedupe_hash="stored-without-sentiment",
        )
    )
    session.commit()

    payload = get_news_sentiment_payload("600519", session=session, market="CN")

    assert payload["summary"] == {"latest_sentiment": None, "article_count": 1}
    assert payload["items"][0]["sentiment"] is None
    assert payload["items"][0]["confidence"] is None


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


def test_akshare_adapter_returns_cn_candidates_without_persisting():
    requested_symbols: list[str] = []
    frame = pd.DataFrame(
        [
            {
                "新闻标题": "Ping An Bank publishes operating update",
                "新闻链接": "https://example.com/pab-update",
                "发布时间": "2026-07-15 14:30:00",
                "文章来源": "eastmoney",
                "新闻内容": "Ping An Bank published an operating update.",
            }
        ]
    )

    def fetcher(symbol: str):
        requested_symbols.append(symbol)
        return frame

    adapter = AkShareNewsSearchAdapter(fetcher=fetcher)
    candidates = adapter.search(
        symbol="000001.SZ",
        query="000001 平安银行 新闻",
        max_results=5,
    )

    assert requested_symbols == ["000001"]
    assert len(candidates) == 1
    assert candidates[0].symbol == "000001.SZ"
    assert candidates[0].provider == "akshare"
    assert candidates[0].source == "eastmoney"
    assert candidates[0].published_at.isoformat() == "2026-07-15T14:30:00+08:00"


def test_yfinance_adapter_maps_exact_cn_market_and_normalizes_nested_news():
    requested_tickers: list[str] = []

    class FakeTicker:
        def get_news(self, *, count: int):
            assert count == 5
            return [
                {
                    "content": {
                        "title": "Ping An Bank market update",
                        "summary": "Ping An Bank published a market update.",
                        "pubDate": "2026-07-15T08:00:00Z",
                        "provider": {"displayName": "Yahoo Finance"},
                        "canonicalUrl": {
                            "url": "https://example.com/pab-yahoo-update"
                        },
                    }
                }
            ]

    def ticker_factory(ticker: str):
        requested_tickers.append(ticker)
        return FakeTicker()

    adapter = YFinanceNewsSearchAdapter(
        market="CN",
        ticker_factory=ticker_factory,
    )
    candidates = adapter.search(
        symbol="000001",
        query="000001 financial news",
        max_results=5,
    )

    assert requested_tickers == ["000001.SZ"]
    assert len(candidates) == 1
    assert candidates[0].provider == "yfinance"
    assert candidates[0].source == "Yahoo Finance"
    assert candidates[0].url == "https://example.com/pab-yahoo-update"
    assert candidates[0].published_at == datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc)


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


def test_refresh_news_stops_after_first_configured_provider_persists_news():
    session = make_session()
    candidate = NewsSearchCandidate(
        symbol="600519",
        query="600519 financial news",
        title="Moutai revenue grows",
        url="https://example.com/moutai-growth",
        source="Example Finance",
        summary="Moutai reports revenue growth.",
        published_at=datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc),
        provider="anspire",
    )

    class SuccessfulAdapter:
        provider = "anspire"

        def search(self, **kwargs):
            return [candidate]

    class UnexpectedAdapter:
        provider = "serpapi_baidu"

        def search(self, **kwargs):
            raise AssertionError("later provider must not run after persisted success")

    result = refresh_news_candidates(
        "600519",
        market="CN",
        session=session,
        settings_payload={
            "news_search_provider_order": ["anspire", "serpapi_baidu"],
            "news_search_enabled_providers": ["anspire", "serpapi_baidu"],
            "news_search_provider_keys": {
                "anspire": "configured",
                "serpapi_baidu": "configured",
            },
            "news_search_max_results": 5,
            "news_search_timeout_seconds": 3,
            "akshare_enabled": True,
        },
        adapters={
            "anspire": SuccessfulAdapter(),
            "serpapi_baidu": UnexpectedAdapter(),
        },
    )

    assert result["status"] == "refreshed"
    assert result["selected_provider"] == "anspire"
    assert result["persisted_article_count"] == 1
    assert result["attempts"] == [
        {"provider": "anspire", "status": "persisted", "candidate_count": 1}
    ]
    assert result["news"]["summary"]["article_count"] == 1
    assert result["diagnostics"][-1]["code"] == "PROVIDER_PERSISTED"


def test_refresh_news_rejects_cross_market_symbol_before_database_or_provider_use():
    session = make_session()
    ingest_mock_news("000001", session=session)

    class UnexpectedAdapter:
        def search(self, **kwargs):
            raise AssertionError("an invalid exact market identity must not call providers")

    result = refresh_news_candidates(
        "000001",
        market="US",
        session=session,
        settings_payload={
            "news_search_provider_order": [],
            "news_search_enabled_providers": [],
            "news_search_provider_keys": {},
            "news_search_max_results": 5,
            "news_search_timeout_seconds": 3,
            "akshare_enabled": False,
        },
        adapters={"yfinance": UnexpectedAdapter()},
    )

    assert result["status"] == "unsupported"
    assert result["selected_provider"] is None
    assert result["attempts"] == []
    assert result["news"]["summary"]["article_count"] == 0
    assert result["diagnostics"][0]["code"] == "UNSUPPORTED_IDENTITY"


def test_refresh_news_rolls_back_persistence_failure_and_uses_next_source(monkeypatch):
    session = make_session()
    first_candidate = NewsSearchCandidate(
        symbol="AAPL",
        query="AAPL financial news",
        title="First provider candidate",
        url="https://example.com/first-provider-candidate",
        source="First Provider",
        summary="This transaction will be rolled back.",
        published_at=datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc),
        provider="anspire",
    )
    fallback_candidate = NewsSearchCandidate(
        symbol="AAPL",
        query="AAPL financial news",
        title="Fallback provider candidate",
        url="https://example.com/fallback-provider-candidate",
        source="Yahoo Finance",
        summary="This candidate should persist after rollback.",
        published_at=datetime(2026, 7, 15, 8, 30, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc),
        provider="yfinance",
    )

    class CandidateAdapter:
        def __init__(self, candidate):
            self.candidate = candidate

        def search(self, **kwargs):
            return [self.candidate]

    original_commit = session.commit
    original_rollback = session.rollback
    commit_count = 0
    rollback_count = 0

    def flaky_commit():
        nonlocal commit_count
        commit_count += 1
        if commit_count == 1:
            raise SQLAlchemyError("private database detail")
        return original_commit()

    def tracked_rollback():
        nonlocal rollback_count
        rollback_count += 1
        return original_rollback()

    monkeypatch.setattr(session, "commit", flaky_commit)
    monkeypatch.setattr(session, "rollback", tracked_rollback)

    result = refresh_news_candidates(
        "AAPL",
        market="US",
        session=session,
        settings_payload={
            "news_search_provider_order": ["anspire"],
            "news_search_enabled_providers": ["anspire"],
            "news_search_provider_keys": {"anspire": "configured"},
            "news_search_max_results": 5,
            "news_search_timeout_seconds": 3,
            "akshare_enabled": False,
        },
        adapters={
            "anspire": CandidateAdapter(first_candidate),
            "yfinance": CandidateAdapter(fallback_candidate),
        },
    )

    assert result["status"] == "refreshed"
    assert result["selected_provider"] == "yfinance"
    assert [attempt["status"] for attempt in result["attempts"]] == [
        "failed",
        "persisted",
    ]
    assert result["diagnostics"][0]["code"] == "PERSISTENCE_ERROR"
    assert rollback_count == 1
    payload = get_news_sentiment_payload("AAPL", session=session, market="US")
    assert [item["title"] for item in payload["items"]] == [
        "Fallback provider candidate"
    ]


def test_refresh_news_falls_back_to_builtin_akshare_for_exact_cn_symbol():
    session = make_session()
    candidate = NewsSearchCandidate(
        symbol="000001",
        query="000001 financial news",
        title="Ping An Bank publishes operating update",
        url="https://example.com/pab-update",
        source="Eastmoney",
        summary="Ping An Bank published an operating update.",
        published_at=datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc),
        provider="akshare",
    )

    class SuccessfulAkShareAdapter:
        provider = "akshare"

        def search(self, **kwargs):
            return [candidate]

    class UnexpectedYFinanceAdapter:
        provider = "yfinance"

        def search(self, **kwargs):
            raise AssertionError("yfinance must not run after AkShare persisted success")

    result = refresh_news_candidates(
        "000001",
        market="CN",
        session=session,
        settings_payload={
            "news_search_provider_order": ["anspire", "serpapi_baidu"],
            "news_search_enabled_providers": ["anspire", "serpapi_baidu"],
            "news_search_provider_keys": {},
            "news_search_max_results": 5,
            "news_search_timeout_seconds": 3,
            "akshare_enabled": True,
        },
        adapters={
            "akshare": SuccessfulAkShareAdapter(),
            "yfinance": UnexpectedYFinanceAdapter(),
        },
    )

    assert result["status"] == "refreshed"
    assert result["selected_provider"] == "akshare"
    assert result["attempts"] == [
        {"provider": "akshare", "status": "persisted", "candidate_count": 1}
    ]
    assert [item["code"] for item in result["diagnostics"]] == [
        "MISSING_CREDENTIALS",
        "MISSING_CREDENTIALS",
        "PROVIDER_PERSISTED",
    ]
    assert result["news"]["items"][0]["title"] == candidate.title


def test_refresh_news_uses_market_aware_yfinance_after_akshare_is_empty():
    session = make_session()
    candidate = NewsSearchCandidate(
        symbol="000001",
        query="000001 financial news",
        title="Ping An Bank market update",
        url="https://example.com/pab-market-update",
        source="Yahoo Finance",
        summary="Ping An Bank market update.",
        published_at=datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc),
        provider="yfinance",
    )

    class EmptyAkShareAdapter:
        provider = "akshare"

        def search(self, **kwargs):
            return []

    class SuccessfulYFinanceAdapter:
        provider = "yfinance"

        def search(self, **kwargs):
            return [candidate]

    result = refresh_news_candidates(
        "000001",
        market="CN",
        session=session,
        settings_payload={
            "news_search_provider_order": ["anspire", "serpapi_baidu"],
            "news_search_enabled_providers": ["anspire", "serpapi_baidu"],
            "news_search_provider_keys": {},
            "news_search_max_results": 5,
            "news_search_timeout_seconds": 3,
            "akshare_enabled": True,
        },
        adapters={
            "akshare": EmptyAkShareAdapter(),
            "yfinance": SuccessfulYFinanceAdapter(),
        },
    )

    assert result["status"] == "refreshed"
    assert result["selected_provider"] == "yfinance"
    assert result["attempts"] == [
        {"provider": "akshare", "status": "empty", "candidate_count": 0},
        {"provider": "yfinance", "status": "persisted", "candidate_count": 1},
    ]
    assert [item["code"] for item in result["diagnostics"]][-2:] == [
        "EMPTY_RESPONSE",
        "PROVIDER_PERSISTED",
    ]
    assert result["news"]["summary"]["article_count"] == 1


def test_refresh_news_reports_no_data_when_every_eligible_source_is_empty():
    session = make_session()

    class EmptyAdapter:
        def search(self, **kwargs):
            return []

    result = refresh_news_candidates(
        "000001",
        market="CN",
        session=session,
        settings_payload={
            "news_search_provider_order": ["anspire", "serpapi_baidu"],
            "news_search_enabled_providers": ["anspire", "serpapi_baidu"],
            "news_search_provider_keys": {},
            "news_search_max_results": 5,
            "news_search_timeout_seconds": 3,
            "akshare_enabled": True,
        },
        adapters={
            "akshare": EmptyAdapter(),
            "yfinance": EmptyAdapter(),
        },
    )

    assert result["status"] == "no_data"
    assert [attempt["provider"] for attempt in result["attempts"]] == [
        "akshare",
        "yfinance",
    ]
    assert [item["code"] for item in result["diagnostics"]] == [
        "MISSING_CREDENTIALS",
        "MISSING_CREDENTIALS",
        "EMPTY_RESPONSE",
        "EMPTY_RESPONSE",
        "DATABASE_FALLBACK_EMPTY",
    ]


def test_refresh_news_never_uses_mock_or_tushare_as_production_fallbacks():
    session = make_session()

    class UnexpectedAdapter:
        def search(self, **kwargs):
            raise AssertionError("mock and Tushare must not run in production refresh")

    class EmptyYFinanceAdapter:
        provider = "yfinance"

        def search(self, **kwargs):
            return []

    result = refresh_news_candidates(
        "AAPL",
        market="US",
        session=session,
        settings_payload={
            "news_search_provider_order": ["mock", "tushare"],
            "news_search_enabled_providers": ["mock", "tushare"],
            "news_search_provider_keys": {},
            "news_search_max_results": 5,
            "news_search_timeout_seconds": 3,
            "akshare_enabled": True,
        },
        adapters={
            "mock": UnexpectedAdapter(),
            "tushare": UnexpectedAdapter(),
            "yfinance": EmptyYFinanceAdapter(),
        },
    )

    assert result["status"] == "no_data"
    assert result["attempts"] == [
        {"provider": "yfinance", "status": "empty", "candidate_count": 0}
    ]


def test_refresh_news_sanitizes_failures_and_never_persists_social_candidates():
    session = make_session()
    social_candidate = NewsSearchCandidate(
        symbol="000001",
        query="000001 financial news",
        title="Ping An Bank discussed on social media",
        url="https://example.com/pab-social",
        source="Example Social",
        summary="Unverified social discussion.",
        published_at=None,
        retrieved_at=datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc),
        provider="serpapi_baidu",
        result_kind="social",
    )

    class FailingConfiguredAdapter:
        provider = "anspire"

        def search(self, **kwargs):
            raise RuntimeError("Bearer private-token cookie=session-secret")

    class SocialOnlyAdapter:
        provider = "serpapi_baidu"

        def search(self, **kwargs):
            return [social_candidate]

    class TimeoutAkShareAdapter:
        provider = "akshare"

        def search(self, **kwargs):
            raise NewsSearchProviderTimeout("private upstream body")

    class EmptyYFinanceAdapter:
        provider = "yfinance"

        def search(self, **kwargs):
            return []

    result = refresh_news_candidates(
        "000001",
        market="CN",
        session=session,
        settings_payload={
            "news_search_provider_order": ["anspire", "serpapi_baidu"],
            "news_search_enabled_providers": ["anspire", "serpapi_baidu"],
            "news_search_provider_keys": {
                "anspire": "configured",
                "serpapi_baidu": "configured",
            },
            "news_search_max_results": 5,
            "news_search_timeout_seconds": 3,
            "akshare_enabled": True,
        },
        adapters={
            "anspire": FailingConfiguredAdapter(),
            "serpapi_baidu": SocialOnlyAdapter(),
            "akshare": TimeoutAkShareAdapter(),
            "yfinance": EmptyYFinanceAdapter(),
        },
    )

    assert result["status"] == "provider_error"
    assert result["selected_provider"] is None
    assert [attempt["status"] for attempt in result["attempts"]] == [
        "failed",
        "empty",
        "timeout",
        "empty",
    ]
    assert [item["code"] for item in result["diagnostics"]] == [
        "PROVIDER_ERROR",
        "NO_PERSISTABLE_CANDIDATES",
        "PROVIDER_TIMEOUT",
        "EMPTY_RESPONSE",
        "DATABASE_FALLBACK_EMPTY",
    ]
    assert result["news"]["summary"]["article_count"] == 0
    serialized = str(result).lower()
    assert "private-token" not in serialized
    assert "session-secret" not in serialized
    assert "upstream body" not in serialized


def test_refresh_news_treats_malformed_provider_output_as_sanitized_error():
    session = make_session()

    class MalformedConfiguredAdapter:
        provider = "anspire"

        def search(self, **kwargs):
            return {"raw": "authorization=private"}

    class EmptyYFinanceAdapter:
        provider = "yfinance"

        def search(self, **kwargs):
            return []

    result = refresh_news_candidates(
        "AAPL",
        market="US",
        session=session,
        settings_payload={
            "news_search_provider_order": ["anspire"],
            "news_search_enabled_providers": ["anspire"],
            "news_search_provider_keys": {"anspire": "configured"},
            "news_search_max_results": 5,
            "news_search_timeout_seconds": 3,
            "akshare_enabled": True,
        },
        adapters={
            "anspire": MalformedConfiguredAdapter(),
            "yfinance": EmptyYFinanceAdapter(),
        },
    )

    assert result["status"] == "provider_error"
    assert result["attempts"][0] == {"provider": "anspire", "status": "failed"}
    assert result["diagnostics"][0]["code"] == "PROVIDER_ERROR"
    assert "private" not in str(result).lower()


def test_refresh_news_rejects_unsafe_or_wrong_symbol_candidates_before_fallback():
    session = make_session()
    unsafe_candidate = NewsSearchCandidate(
        symbol="MSFT",
        query="AAPL financial news",
        title="Wrong symbol candidate",
        url="javascript:alert('unsafe')",
        source="Unsafe Provider",
        summary="This row must not be persisted.",
        published_at=datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc),
        provider="anspire",
    )
    fallback_candidate = NewsSearchCandidate(
        symbol="AAPL",
        query="AAPL financial news",
        title="Safe fallback candidate",
        url="https://example.com/safe-fallback-candidate",
        source="Yahoo Finance",
        summary="A safe exact-symbol candidate.",
        published_at=datetime(2026, 7, 15, 8, 30, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc),
        provider="yfinance",
    )

    class CandidateAdapter:
        def __init__(self, candidate):
            self.candidate = candidate

        def search(self, **kwargs):
            return [self.candidate]

    result = refresh_news_candidates(
        "AAPL",
        market="US",
        session=session,
        settings_payload={
            "news_search_provider_order": ["anspire"],
            "news_search_enabled_providers": ["anspire"],
            "news_search_provider_keys": {"anspire": "configured"},
            "news_search_max_results": 5,
            "news_search_timeout_seconds": 3,
            "akshare_enabled": False,
        },
        adapters={
            "anspire": CandidateAdapter(unsafe_candidate),
            "yfinance": CandidateAdapter(fallback_candidate),
        },
    )

    assert result["status"] == "refreshed"
    assert result["selected_provider"] == "yfinance"
    assert result["attempts"] == [
        {"provider": "anspire", "status": "failed"},
        {"provider": "yfinance", "status": "persisted", "candidate_count": 1},
    ]
    assert result["diagnostics"][0]["code"] == "PROVIDER_INVALID_CANDIDATE"
    payload = get_news_sentiment_payload("AAPL", session=session, market="US")
    assert [item["title"] for item in payload["items"]] == ["Safe fallback candidate"]


def test_refresh_news_rejects_credential_urls_and_oversized_persistence_fields():
    retrieved_at = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)
    invalid_candidates = [
        NewsSearchCandidate(
            symbol="AAPL",
            query="AAPL financial news",
            title="Credential URL candidate",
            url="https://private-user:private-password@example.com/article",
            source="Unsafe Provider",
            summary="Must be rejected.",
            published_at=retrieved_at,
            retrieved_at=retrieved_at,
            provider="anspire",
        ),
        NewsSearchCandidate(
            symbol="AAPL",
            query="AAPL financial news",
            title="T" * 513,
            url="https://example.com/oversized-title",
            source="Unsafe Provider",
            summary="Must be rejected.",
            published_at=retrieved_at,
            retrieved_at=retrieved_at,
            provider="anspire",
        ),
        NewsSearchCandidate(
            symbol="AAPL",
            query="AAPL financial news",
            title="Oversized URL candidate",
            url="https://example.com/" + ("u" * 1025),
            source="Unsafe Provider",
            summary="Must be rejected.",
            published_at=retrieved_at,
            retrieved_at=retrieved_at,
            provider="anspire",
        ),
        NewsSearchCandidate(
            symbol="AAPL",
            query="AAPL financial news",
            title="Oversized source candidate",
            url="https://example.com/oversized-source",
            source="S" * 129,
            summary="Must be rejected.",
            published_at=retrieved_at,
            retrieved_at=retrieved_at,
            provider="anspire",
        ),
    ]

    class CandidateAdapter:
        def __init__(self, candidate):
            self.candidate = candidate

        def search(self, **kwargs):
            return [self.candidate]

    class EmptyYFinanceAdapter:
        def search(self, **kwargs):
            return []

    for invalid_candidate in invalid_candidates:
        session = make_session()
        result = refresh_news_candidates(
            "AAPL",
            market="US",
            session=session,
            settings_payload={
                "news_search_provider_order": ["anspire"],
                "news_search_enabled_providers": ["anspire"],
                "news_search_provider_keys": {"anspire": "configured"},
                "news_search_max_results": 5,
                "news_search_timeout_seconds": 3,
                "akshare_enabled": False,
            },
            adapters={
                "anspire": CandidateAdapter(invalid_candidate),
                "yfinance": EmptyYFinanceAdapter(),
            },
        )

        assert result["status"] == "provider_error"
        assert result["attempts"][0] == {
            "provider": "anspire",
            "status": "failed",
        }
        assert result["diagnostics"][0]["code"] == "PROVIDER_INVALID_CANDIDATE"
        assert session.query(NewsArticle).count() == 0
        serialized = str(result).lower()
        assert "private-user" not in serialized
        assert "private-password" not in serialized


def test_search_ingest_rejects_invalid_provider_batch_and_persists_safe_fallback():
    session = make_session()
    retrieved_at = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)
    invalid_candidate = NewsSearchCandidate(
        symbol="MSFT",
        query="AAPL financial news",
        title="Wrong instrument candidate",
        url="https://private-user:private-password@example.com/wrong",
        source="Unsafe Provider",
        summary="Must not be exposed or persisted.",
        published_at=retrieved_at,
        retrieved_at=retrieved_at,
        provider="anspire",
    )
    safe_candidate = NewsSearchCandidate(
        symbol="AAPL",
        query="AAPL financial news",
        title="Safe provider fallback",
        url="https://example.com/safe-search-ingest-fallback",
        source="Safe Provider",
        summary="Exact-symbol safe news.",
        published_at=retrieved_at,
        retrieved_at=retrieved_at,
        provider="serpapi_baidu",
    )

    class CandidateAdapter:
        def __init__(self, candidate):
            self.candidate = candidate

        def search(self, **kwargs):
            return [self.candidate]

    result = search_and_ingest_news_candidates(
        "AAPL",
        session=session,
        settings_payload={
            "news_search_provider_order": ["anspire", "serpapi_baidu"],
            "news_search_enabled_providers": ["anspire", "serpapi_baidu"],
            "news_search_provider_keys": {
                "anspire": "configured",
                "serpapi_baidu": "configured",
            },
            "news_search_max_results": 5,
            "news_search_timeout_seconds": 3,
        },
        adapters={
            "anspire": CandidateAdapter(invalid_candidate),
            "serpapi_baidu": CandidateAdapter(safe_candidate),
        },
    )

    assert result["status"] == "ingested"
    assert result["candidate_count"] == 1
    assert result["article_count"] == 1
    assert [item["code"] for item in result["diagnostics"]][:2] == [
        "PROVIDER_INVALID_CANDIDATE",
        "PROVIDER_OK",
    ]
    assert [item["title"] for item in result["candidates"]] == [
        "Safe provider fallback"
    ]
    assert [article.title for article in session.query(NewsArticle).all()] == [
        "Safe provider fallback"
    ]
    serialized = str(result).lower()
    assert "private-user" not in serialized
    assert "private-password" not in serialized


def test_shared_news_persistence_rejects_unsafe_candidate():
    session = make_session()
    retrieved_at = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)
    candidate = NewsSearchCandidate(
        symbol="AAPL",
        query="AAPL financial news",
        title="Unsafe direct candidate",
        url="javascript:alert('unsafe')",
        source="Unsafe Provider",
        summary="Must not persist.",
        published_at=retrieved_at,
        retrieved_at=retrieved_at,
        provider="anspire",
    )

    counts = persist_news_search_candidates(
        [candidate],
        session=session,
        expected_symbol="AAPL",
        expected_provider="anspire",
    )

    assert counts == (0, 0)
    assert session.query(NewsArticle).count() == 0


@pytest.mark.parametrize(
    "credential_url",
    [
        "https://example.com/article?access_token=private",
        "https://example.com/article?utm_source=feed&apiKey=private",
        "https://example.com/article#token=private",
        "https://example.com/article#/reader?X-Amz-Signature=private",
    ],
)
def test_news_candidate_credential_urls_are_never_returned_or_persisted(
    credential_url,
):
    session = make_session()
    candidate = NewsSearchCandidate(
        symbol="AAPL",
        query="AAPL financial news",
        title="Credential-bearing candidate",
        url=credential_url,
        source="Unsafe Provider",
        summary="This candidate must be rejected.",
        published_at=datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc),
        provider="anspire",
    )

    class CandidateAdapter:
        def search(self, **_kwargs):
            return [candidate]

    result = search_news_candidates(
        "AAPL",
        session=session,
        settings_payload={
            "news_search_provider_order": ["anspire"],
            "news_search_enabled_providers": ["anspire"],
            "news_search_provider_keys": {"anspire": "configured"},
            "news_search_max_results": 5,
            "news_search_timeout_seconds": 3,
        },
        adapters={"anspire": CandidateAdapter()},
    )

    assert result["candidates"] == []
    assert result["diagnostics"][0]["code"] == "PROVIDER_INVALID_CANDIDATE"
    assert credential_url not in str(result)
    assert persist_news_search_candidates(
        [candidate],
        session=session,
        expected_symbol="AAPL",
        expected_provider="anspire",
    ) == (0, 0)
    assert session.query(NewsArticle).count() == 0


def test_news_candidate_preserves_ordinary_query_params():
    session = make_session()
    url = "https://example.com/article?utm_source=feed&page=2#section"
    candidate = NewsSearchCandidate(
        symbol="AAPL",
        query="AAPL financial news",
        title="Ordinary public news URL",
        url=url,
        source="Example Finance",
        summary="An ordinary public news summary.",
        published_at=datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc),
        provider="anspire",
    )

    assert persist_news_search_candidates(
        [candidate],
        session=session,
        expected_symbol="AAPL",
        expected_provider="anspire",
    ) == (1, 1)
    assert session.query(NewsArticle).one().url == url


def test_news_candidate_summary_is_plain_bounded_text_before_return_and_storage():
    session = make_session()
    raw_summary = (
        "<p>Revenue&nbsp;  improved</p>"
        "<script>Authorization: Bearer private</script>"
        f"<div>{'operating update ' * 100}</div>"
    )
    candidate = NewsSearchCandidate(
        symbol="AAPL",
        query="AAPL financial news",
        title="Apple operating update",
        url="https://example.com/apple-operating-update",
        source="Example Finance",
        summary=raw_summary,
        published_at=datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc),
        provider="anspire",
    )

    class CandidateAdapter:
        def search(self, **_kwargs):
            return [candidate]

    result = search_news_candidates(
        "AAPL",
        session=session,
        settings_payload={
            "news_search_provider_order": ["anspire"],
            "news_search_enabled_providers": ["anspire"],
            "news_search_provider_keys": {"anspire": "configured"},
            "news_search_max_results": 5,
            "news_search_timeout_seconds": 3,
        },
        adapters={"anspire": CandidateAdapter()},
    )
    summary = result["candidates"][0]["summary"]

    assert summary.startswith("Revenue improved operating update")
    assert len(summary) == 1000
    assert "<" not in summary
    assert "  " not in summary
    assert "Bearer private" not in summary
    assert persist_news_search_candidates(
        [candidate],
        session=session,
        expected_symbol="AAPL",
        expected_provider="anspire",
    ) == (1, 1)
    assert session.query(NewsArticle).one().summary == summary


def test_shared_news_persistence_rejects_invalid_batch_atomically():
    session = make_session()
    retrieved_at = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)
    safe_candidate = NewsSearchCandidate(
        symbol="AAPL",
        query="AAPL financial news",
        title="Safe candidate must not be partially written",
        url="https://example.com/safe-atomic-candidate",
        source="Example Finance",
        summary="A safe candidate in an invalid provider batch.",
        published_at=retrieved_at,
        retrieved_at=retrieved_at,
        provider="anspire",
    )
    sensitive_candidate = NewsSearchCandidate(
        symbol="AAPL",
        query="AAPL financial news",
        title="Sensitive candidate",
        url="https://example.com/sensitive-candidate",
        source="Unsafe Provider",
        summary="Cookie: session=private-value",
        published_at=retrieved_at,
        retrieved_at=retrieved_at,
        provider="anspire",
    )

    assert persist_news_search_candidates(
        [safe_candidate, sensitive_candidate],
        session=session,
        expected_symbol="AAPL",
        expected_provider="anspire",
    ) == (0, 0)
    assert session.query(NewsArticle).count() == 0


@pytest.mark.parametrize(
    "sensitive_summary",
    [
        "Bearer eyJhbGciOiJIUzI1NiJ9.private",
        '{"access_token":"private-value"}',
        '{"Authorization":"Bearer private-value"}',
    ],
)
def test_shared_news_persistence_rejects_sensitive_text_shapes_atomically(
    sensitive_summary,
):
    session = make_session()
    retrieved_at = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)
    safe_candidate = NewsSearchCandidate(
        symbol="AAPL",
        query="AAPL financial news",
        title="Safe candidate must not be partially written",
        url="https://example.com/safe-sensitive-text-batch",
        source="Example Finance",
        summary="A safe candidate in a sensitive provider batch.",
        published_at=retrieved_at,
        retrieved_at=retrieved_at,
        provider="anspire",
    )
    sensitive_candidate = NewsSearchCandidate(
        symbol="AAPL",
        query="AAPL financial news",
        title="Sensitive provider text candidate",
        url="https://example.com/sensitive-provider-text",
        source="Unsafe Provider",
        summary=sensitive_summary,
        published_at=retrieved_at,
        retrieved_at=retrieved_at,
        provider="anspire",
    )

    assert persist_news_search_candidates(
        [safe_candidate, sensitive_candidate],
        session=session,
        expected_symbol="AAPL",
        expected_provider="anspire",
    ) == (0, 0)
    assert session.query(NewsArticle).count() == 0


def test_news_candidate_batch_rejects_malformed_dataclass_fields_without_crashing():
    session = make_session()
    malformed_candidate = NewsSearchCandidate(
        symbol="AAPL",
        query="AAPL financial news",
        title="Malformed candidate",
        url="https://example.com/malformed-candidate",
        source="Unsafe Provider",
        summary={"raw": "provider body"},
        published_at=datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc),
        provider="anspire",
    )

    class CandidateAdapter:
        def search(self, **_kwargs):
            return [malformed_candidate]

    result = search_news_candidates(
        "AAPL",
        session=session,
        settings_payload={
            "news_search_provider_order": ["anspire"],
            "news_search_enabled_providers": ["anspire"],
            "news_search_provider_keys": {"anspire": "configured"},
            "news_search_max_results": 5,
            "news_search_timeout_seconds": 3,
        },
        adapters={"anspire": CandidateAdapter()},
    )

    assert result["candidates"] == []
    assert result["diagnostics"][0]["code"] == "PROVIDER_INVALID_CANDIDATE"
    assert persist_news_search_candidates(
        [malformed_candidate],
        session=session,
        expected_symbol="AAPL",
        expected_provider="anspire",
    ) == (0, 0)
    assert session.query(NewsArticle).count() == 0


def test_legacy_yfinance_ingest_uses_shared_news_safety_boundary(monkeypatch):
    session = make_session()
    ticker = type(
        "Ticker",
        (),
        {
            "news": [
                {
                    "title": "Credential URL row",
                    "link": "https://example.com/private?token=private",
                    "publisher": "Unsafe Provider",
                    "summary": "Must not persist.",
                },
                {
                    "title": "Structured provider body row",
                    "link": "https://example.com/structured-body",
                    "publisher": "Unsafe Provider",
                    "summary": {"raw": "provider response body"},
                },
                {
                    "title": "Safe yfinance row",
                    "link": "https://example.com/public?utm_source=feed",
                    "publisher": "Example Finance",
                    "summary": "<p>Verified&nbsp; update</p>" + (" detail" * 300),
                },
            ]
        },
    )()
    monkeypatch.setattr("yfinance.Ticker", lambda _symbol: ticker)

    result = ingest_yfinance_news("AAPL", session=session)

    assert result["article_count"] == 1
    article = session.query(NewsArticle).one()
    assert article.title == "Safe yfinance row"
    assert article.url == "https://example.com/public?utm_source=feed"
    assert article.summary.startswith("Verified update detail")
    assert len(article.summary) == 1000
    assert "<" not in article.summary


def test_legacy_akshare_ingest_uses_shared_news_safety_boundary(monkeypatch):
    session = make_session()
    frame = pd.DataFrame(
        [
            {
                "新闻标题": "Credential URL row",
                "新闻链接": "https://example.com/private#sig=private",
                "发布时间": "2026-07-15 09:00:00",
                "新闻内容": "Must not persist.",
                "文章来源": "Unsafe Provider",
            },
            {
                "新闻标题": "Sensitive summary row",
                "新闻链接": "https://example.com/sensitive-summary",
                "发布时间": "2026-07-15 09:05:00",
                "新闻内容": "Authorization: Bearer private-value",
                "文章来源": "Unsafe Provider",
            },
            {
                "新闻标题": "Structured provider body row",
                "新闻链接": "https://example.com/structured-body",
                "发布时间": "2026-07-15 09:07:00",
                "新闻内容": {"raw": "provider response body"},
                "文章来源": "Unsafe Provider",
            },
            {
                "新闻标题": "Safe AkShare row",
                "新闻链接": "https://example.com/public?page=2",
                "发布时间": "2026-07-15 09:10:00",
                "新闻内容": "<p>公司&nbsp; 公告</p>" + (" 经营更新" * 300),
                "文章来源": "Example Finance",
            },
        ]
    )
    monkeypatch.setattr("akshare.stock_news_em", lambda symbol: frame)

    result = ingest_akshare_news("600519", session=session)

    assert result["article_count"] == 1
    article = session.query(NewsArticle).one()
    assert article.title == "Safe AkShare row"
    assert article.url == "https://example.com/public?page=2"
    assert article.summary.startswith("公司 公告 经营更新")
    assert len(article.summary) == 1000
    assert "<" not in article.summary


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
