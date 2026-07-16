import re
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import GeneratedReport, MarketDailyEvidenceEvent, NewsArticle
from packages.providers.base import ProviderBar
from packages.services.market_dashboard import _serialize_market_index, get_market_overview_payload
from packages.services.market_indices import DEFAULT_MARKET_INDICES
from packages.services.market_data import MarketDataProviderUnavailableError
from packages.services.research_source_notes import ResearchSourceNoteInput, create_research_source_note
from packages.shared.cache import clear_market_overview_cache
from packages.shared.database import Base


class FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}
        self.expirations: dict[str, int] = {}

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value
        if ex is not None:
            self.expirations[key] = ex


def _bars_payload(symbol: str, *, status: str = "ok", close: float = 101.0):
    items = [] if status == "no_data" else [
        {
            "timestamp": "2026-07-09",
            "open": close - 1,
            "high": close + 1,
            "low": close - 2,
            "close": close,
            "volume": 1000,
        }
    ]
    return {
        "symbol": symbol,
        "timeframe": "1d",
        "source": "yfinance",
        "provider": "yfinance",
        "requested_provider": "yfinance",
        "effective_provider": "yfinance",
        "status": status,
        "no_data_reason": "No daily bars were available." if status == "no_data" else None,
        "items": items,
    }


class FailingRedis:
    def get(self, key: str) -> str | None:
        raise RuntimeError("redis read unavailable")

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        raise RuntimeError("redis write unavailable")


@pytest.fixture(autouse=True)
def disable_dashboard_llm(monkeypatch):
    monkeypatch.setattr(
        "packages.services.market_dashboard.get_platform_settings",
        lambda: {
            "market_data_provider": "mock",
            "llm_provider": "mock",
            "llm_api_key": "",
            "llm_api_base": "https://api.openai.com/v1",
        },
    )


def make_session():
    clear_market_overview_cache("mock")
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_cn_index_keeps_valid_yfinance_result_without_sina_call(monkeypatch):
    session = make_session()
    index = DEFAULT_MARKET_INDICES[0]
    monkeypatch.setattr(
        "packages.services.market_dashboard.get_bars_payload",
        lambda symbol, *_args, **_kwargs: _bars_payload(symbol),
    )

    class UnexpectedAkShareProvider:
        def __init__(self):
            raise AssertionError("valid yfinance index data must not call Sina")

    monkeypatch.setattr(
        "packages.services.market_dashboard.AkShareProvider",
        UnexpectedAkShareProvider,
    )

    item, diagnostic = _serialize_market_index(
        index=index,
        session=session,
        provider_name="yfinance",
        start=date(2026, 7, 1),
        end=date(2026, 7, 10),
        today=date(2026, 7, 10),
    )

    assert diagnostic is None
    assert item["provider"] == "yfinance"
    assert item["latest"]["close"] == 101.0


@pytest.mark.parametrize(
    "primary_payload",
    [
        _bars_payload("000001.SS", status="no_data"),
        _bars_payload("000001.SS", close=float("nan")),
    ],
)
def test_cn_index_uses_one_coherent_sina_fallback_for_empty_or_invalid_yfinance(
    monkeypatch,
    primary_payload,
):
    session = make_session()
    index = DEFAULT_MARKET_INDICES[0]
    calls: list[tuple[str, date, date]] = []
    monkeypatch.setattr(
        "packages.services.market_dashboard.get_bars_payload",
        lambda *_args, **_kwargs: primary_payload,
    )

    class FakeAkShareProvider:
        def fetch_index_bars(self, symbol, start, end):
            calls.append((symbol, start, end))
            return [
                ProviderBar(
                    symbol=symbol,
                    timestamp=date(2026, 7, 9),
                    open=Decimal("100"),
                    high=Decimal("102"),
                    low=Decimal("99"),
                    close=Decimal("101"),
                    volume=Decimal("1000"),
                )
            ]

    monkeypatch.setattr(
        "packages.services.market_dashboard.AkShareProvider",
        FakeAkShareProvider,
    )

    item, diagnostic = _serialize_market_index(
        index=index,
        session=session,
        provider_name="yfinance",
        start=date(2026, 7, 1),
        end=date(2026, 7, 10),
        today=date(2026, 7, 10),
    )

    assert diagnostic is None
    assert calls == [("000001", date(2026, 7, 1), date(2026, 7, 10))]
    assert item["bars"] == [
        {
            "timestamp": "2026-07-09",
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 1000.0,
            "amount": None,
        }
    ]
    assert item["provider"] == "akshare"
    assert item["source"] == "akshare.stock_zh_index_daily"
    assert item["requested_provider"] == "yfinance"
    assert item["effective_provider"] == "akshare"


def test_cn_index_sina_failure_is_sanitized_and_not_retried(monkeypatch):
    session = make_session()
    index = DEFAULT_MARKET_INDICES[0]
    calls = 0
    monkeypatch.setattr(
        "packages.services.market_dashboard.get_bars_payload",
        lambda symbol, *_args, **_kwargs: _bars_payload(symbol, status="no_data"),
    )

    class FailingAkShareProvider:
        def fetch_index_bars(self, symbol, start, end):
            nonlocal calls
            calls += 1
            raise ConnectionError("https://secret.example/index?token=do-not-expose")

    monkeypatch.setattr(
        "packages.services.market_dashboard.AkShareProvider",
        FailingAkShareProvider,
    )

    item, diagnostic = _serialize_market_index(
        index=index,
        session=session,
        provider_name="yfinance",
        start=date(2026, 7, 1),
        end=date(2026, 7, 10),
        today=date(2026, 7, 10),
    )

    assert calls == 1
    assert item["status"] == "unavailable"
    assert item["provider"] == "akshare"
    assert item["no_data_reason"] == "AkShare Sina index fallback failed."
    assert diagnostic == {
        "section": "indices",
        "code": index.code,
        "status": "unavailable",
        "message": "AkShare Sina index fallback failed.",
        "details": {"provider": "akshare", "exception_type": "ConnectionError"},
    }


def test_cn_index_empty_sina_fallback_remains_explicit_no_data(monkeypatch):
    session = make_session()
    index = DEFAULT_MARKET_INDICES[0]
    monkeypatch.setattr(
        "packages.services.market_dashboard.get_bars_payload",
        lambda symbol, *_args, **_kwargs: _bars_payload(symbol, status="no_data"),
    )

    class EmptyAkShareProvider:
        def fetch_index_bars(self, symbol, start, end):
            return []

    monkeypatch.setattr(
        "packages.services.market_dashboard.AkShareProvider",
        EmptyAkShareProvider,
    )

    item, diagnostic = _serialize_market_index(
        index=index,
        session=session,
        provider_name="yfinance",
        start=date(2026, 7, 1),
        end=date(2026, 7, 10),
        today=date(2026, 7, 10),
    )

    assert diagnostic is None
    assert item["status"] == "no_data"
    assert item["bars"] == []
    assert item["provider"] == "akshare"
    assert item["requested_provider"] == "yfinance"


def test_non_cn_index_never_uses_sina_fallback(monkeypatch):
    session = make_session()
    index = next(item for item in DEFAULT_MARKET_INDICES if item.code == "us_sp_500")
    monkeypatch.setattr(
        "packages.services.market_dashboard.get_bars_payload",
        lambda symbol, *_args, **_kwargs: _bars_payload(symbol, status="no_data"),
    )

    class UnexpectedAkShareProvider:
        def __init__(self):
            raise AssertionError("non-CN indices must not call Sina")

    monkeypatch.setattr(
        "packages.services.market_dashboard.AkShareProvider",
        UnexpectedAkShareProvider,
    )

    item, diagnostic = _serialize_market_index(
        index=index,
        session=session,
        provider_name="yfinance",
        start=date(2026, 7, 1),
        end=date(2026, 7, 10),
        today=date(2026, 7, 10),
    )

    assert diagnostic is None
    assert item["status"] == "no_data"
    assert item["provider"] == "yfinance"


def test_market_overview_payload_contains_followed_indices_and_valuation_sections():
    session = make_session()

    payload = get_market_overview_payload(
        session=session,
        provider_name="mock",
        today=date(2026, 7, 3),
    )

    assert payload["provider"] == "mock"
    assert payload["range"] == {
        "timeframe": "1d",
        "start": "2026-04-02",
        "end": "2026-07-03",
    }

    followed_items = payload["followed"]["items"]
    assert payload["followed"]["scope"] == "watchlist"
    assert len(followed_items) == 1
    assert followed_items[0]["symbol"] == "AAPL"
    assert followed_items[0]["detail_path"] == "/instruments/AAPL"
    assert followed_items[0]["status"] == "ok"
    assert followed_items[0]["latest"]["movement"]["direction"] == "up"

    index_items = payload["indices"]["items"]
    assert len(index_items) == 10
    assert index_items[0]["code"] == "cn_shanghai_composite"
    assert index_items[0]["provider_symbol"] == "SH000001"
    assert index_items[-1]["code"] == "us_dow_jones"

    valuation_items = payload["valuation_indicators"]["items"]
    assert payload["macro_indicators"]["items"] == valuation_items
    assert [item["code"] for item in valuation_items] == [
        "buffett_indicator_cn",
        "buffett_indicator_hk",
        "buffett_indicator_us",
        "us_10y_yield",
        "us_2y_yield",
        "us_10y_2y_spread",
        "us_cpi_yoy",
        "us_m2_yoy",
        "cn_m2_yoy",
    ]
    assert all(item["status"] == "no_data" for item in valuation_items)

    dashboard_brief = payload["dashboard_brief"]
    assert dashboard_brief["status"] == "degraded"
    assert dashboard_brief["safety"]["not_investment_advice"] is True
    assert dashboard_brief["sections"][0]["id"] == "what_changed"
    assert "no audited observations" in dashboard_brief["sections"][0]["items"][0]
    assert dashboard_brief["diagnostics"][0]["code"] == "MACRO_INDICATOR_NO_DATA"
    assert "generated reports and 0 stored news items" in dashboard_brief["sections"][1]["items"][2]
    assert {diagnostic["code"] for diagnostic in dashboard_brief["diagnostics"]} >= {
        "GENERATED_REPORTS_NO_DATA",
        "NEWS_NO_DATA",
        "FALLBACK_USED",
    }
    narrative = dashboard_brief["narrative"]
    assert narrative["model"] == {
        "provider": "deterministic",
        "name": "dashboard-brief-deterministic-fallback",
        "used_llm": False,
        "fallback_reason": "OpenAI-compatible LLM provider is not configured.",
    }
    assert "not investment advice" in narrative["answer_markdown"]
    assert narrative["context"]["source_mix"] == {
        "macro_citations": 0,
            "report_citations": 0,
        "news_citations": 0,
        "research_source_note_citations": 0,
        "market_daily_citations": 0,
        "information_source_gaps": 11,
    }

    information_sources = payload["information_sources"]
    assert information_sources["status"] == "degraded"
    assert information_sources["summary"]["needs_action"] == 9
    assert information_sources["items"][0]["id"] == "fred_us_rates"


def test_market_overview_brief_includes_report_and_news_availability():
    session = make_session()
    session.add(
        GeneratedReport(
            symbol="AAPL",
            report_type="stock_daily",
            as_of=date(2026, 7, 2),
            content_markdown="AAPL daily research report.",
            citations=["bars_1d:AAPL:2026-07-02"],
            source_summary={"source": "mock"},
        )
    )
    session.add(
        NewsArticle(
            symbol="AAPL",
            title="Apple reports strong growth in services revenue",
            url="https://example.com/aapl-services-growth",
            source="mock_news",
            published_at=datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc),
            summary="Apple reports strong growth and record services profit in the quarter.",
            dedupe_hash="aapl-services-growth",
        )
    )
    session.add(
        MarketDailyEvidenceEvent(
            event_type="hot_sector",
            identity="semiconductor",
            identity_name="Semiconductor",
            market="CN",
            trade_date=date(2026, 7, 2),
            provider="fake",
            source="fake_hot_sector",
            as_of=datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc),
            payload_json={"sector_id": "semiconductor", "name": "Semiconductor", "fund_flow": 999.0},
            availability_json={"status": "delayed"},
            provider_capabilities_json={"ranking": {"status": "delayed"}},
            diagnostics_json=[],
        )
    )
    session.commit()
    source_note = create_research_source_note(
        ResearchSourceNoteInput(
            title="AAPL hard-to-find source review",
            source_name="Manual research notebook",
            source_type="valuation_component",
            source_url="https://example.com/aapl-valuation-source",
            symbols=["AAPL"],
            excerpt="Reviewed source excerpt for valuation context.",
            ai_follow_up="Summarize how this source supports Buffett Indicator context.",
            review_status="reviewed",
            is_citable=True,
            source_id="buffett_manual_valuation_components",
            target_indicator_codes=["buffett_indicator_us"],
            component_role="market_cap",
            methodology_note="Reviewed market-cap component.",
            license_note="Public source for personal research review.",
        ),
        session=session,
    )
    create_research_source_note(
        ResearchSourceNoteInput(
            title="Draft source note",
            source_name="Manual research notebook",
            source_type="valuation_component",
            source_url="https://example.com/aapl-draft",
            symbols=["AAPL"],
            excerpt="Draft source excerpt.",
            ai_follow_up="Check whether this draft source is useful later.",
            review_status="draft",
            is_citable=False,
        ),
        session=session,
    )
    create_research_source_note(
        ResearchSourceNoteInput(
            title="Reviewed collection note",
            source_name="Manual research notebook",
            source_type="valuation_component",
            source_url="https://example.com/aapl-reviewed-collection",
            symbols=["AAPL"],
            excerpt="Reviewed but not citable source excerpt.",
            review_status="reviewed",
            is_citable=False,
        ),
        session=session,
    )

    payload = get_market_overview_payload(
        session=session,
        provider_name="mock",
        today=date(2026, 7, 3),
    )

    dashboard_brief = payload["dashboard_brief"]
    assert "1 generated reports and 1 stored news items" in dashboard_brief["sections"][1]["items"][2]
    citation_sources = {citation["source"] for citation in dashboard_brief["citations"]}
    assert citation_sources >= {
        "generated_reports",
        "news",
        "research_source_notes",
        "market_daily_evidence",
    }
    citation_ids = {citation["id"] for citation in dashboard_brief["citations"]}
    assert source_note["citation_id"] in citation_ids
    assert "market_daily_event:hot_sector:semiconductor:2026-07-02" in citation_ids
    source_note_citation = next(
        citation for citation in dashboard_brief["citations"] if citation["id"] == source_note["citation_id"]
    )
    assert source_note_citation["metadata"]["source_id"] == "buffett_manual_valuation_components"
    assert source_note_citation["metadata"]["target_indicator_codes"] == ["buffett_indicator_us"]
    assert source_note_citation["metadata"]["component_role"] == "market_cap"
    assert source_note_citation["metadata"]["completeness"]["status"] == "partial"
    citation_labels = {citation["label"] for citation in dashboard_brief["citations"]}
    assert "Draft source note" not in citation_labels
    assert "Reviewed collection note" not in citation_labels
    assert dashboard_brief["narrative"]["context"]["source_mix"]["report_citations"] == 1
    assert dashboard_brief["narrative"]["context"]["source_mix"]["news_citations"] == 1
    assert dashboard_brief["narrative"]["context"]["source_mix"]["research_source_note_citations"] == 1
    assert dashboard_brief["narrative"]["context"]["source_mix"]["market_daily_citations"] == 1
    diagnostic_codes = {diagnostic["code"] for diagnostic in dashboard_brief["diagnostics"]}
    assert "GENERATED_REPORTS_NO_DATA" not in diagnostic_codes
    assert "NEWS_NO_DATA" not in diagnostic_codes

    follow_up_queue = payload["research_follow_up_queue"]
    follow_up_items = {item["id"]: item for item in follow_up_queue["items"]}
    assert follow_up_queue["safety"]["not_investment_advice"] is True
    assert follow_up_queue["summary"]["ai_summary_question"] == 2
    assert follow_up_queue["summary"]["source_gap"] >= 1
    assert (
        follow_up_items[f"source_note_ai_follow_up:{source_note['id']}"]["citation_id"]
        == source_note["citation_id"]
    )
    draft_follow_up = next(
        item for item in follow_up_queue["items"] if item["id"].startswith("source_note_ai_follow_up:") and item["note_title"] == "Draft source note"
    )
    assert draft_follow_up["citation_policy"] == "collection_only"
    assert "citation_id" not in draft_follow_up
    source_gap_ids = {item.get("citation_id") for item in follow_up_queue["items"] if item["kind"] == "source_gap"}
    assert source_gap_ids == {None}


def test_market_overview_degrades_when_source_notebook_is_unavailable(monkeypatch):
    session = make_session()

    def fail_source_note_lookup(*args, **kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(
        "packages.services.market_dashboard.list_citable_research_source_note_citations",
        fail_source_note_lookup,
    )

    payload = get_market_overview_payload(
        session=session,
        provider_name="mock",
        today=date(2026, 7, 3),
    )

    diagnostic_codes = {diagnostic["code"] for diagnostic in payload["dashboard_brief"]["diagnostics"]}
    assert "SOURCE_UNAVAILABLE" in diagnostic_codes
    assert payload["dashboard_brief"]["narrative"]["context"]["source_mix"]["research_source_note_citations"] == 0


def test_market_overview_brief_uses_llm_when_configured(monkeypatch):
    session = make_session()
    session.add(
        GeneratedReport(
            symbol="AAPL",
            report_type="stock_daily",
            as_of=date(2026, 7, 2),
            content_markdown="AAPL daily research report.",
            citations=["bars_1d:AAPL:2026-07-02"],
            source_summary={"source": "mock"},
        )
    )
    session.commit()

    class FakeDashboardLLMProvider:
        def generate(self, prompt: str) -> str:
            assert "Allowed citations" in prompt
            assert "Source readiness gaps, not citations" in prompt
            match = re.search(r"\[(generated_report:[^\]]+)\]", prompt)
            assert match is not None
            return f"### Summary\nGenerated dashboard synthesis [{match.group(1)}]."

    monkeypatch.setattr(
        "packages.services.market_dashboard.get_platform_settings",
        lambda: {
            "market_data_provider": "mock",
            "llm_provider": "openai",
            "llm_api_key": "test-key",
            "llm_api_base": "https://example.test/v1",
            "llm_model": "  deepseek-chat  ",
        },
    )
    monkeypatch.setattr(
        "packages.services.market_dashboard.get_llm_provider",
        lambda _settings=None: FakeDashboardLLMProvider(),
    )

    payload = get_market_overview_payload(
        session=session,
        provider_name="mock",
        today=date(2026, 7, 3),
    )

    narrative = payload["dashboard_brief"]["narrative"]
    assert narrative["answer_markdown"].startswith("### Summary\nGenerated dashboard synthesis")
    assert narrative["model"] == {
        "provider": "openai",
        "name": "deepseek-chat",
        "used_llm": True,
        "fallback_reason": None,
    }
    diagnostic_codes = {diagnostic["code"] for diagnostic in payload["dashboard_brief"]["diagnostics"]}
    assert "FALLBACK_USED" not in diagnostic_codes


def test_market_overview_brief_rejects_unknown_llm_citation(monkeypatch):
    session = make_session()
    session.add(
        GeneratedReport(
            symbol="AAPL",
            report_type="stock_daily",
            as_of=date(2026, 7, 2),
            content_markdown="AAPL daily research report.",
            citations=["bars_1d:AAPL:2026-07-02"],
            source_summary={"source": "mock"},
        )
    )
    session.commit()

    class FakeDashboardLLMProvider:
        def generate(self, prompt: str) -> str:
            assert "Allowed citations" in prompt
            return "### Summary\nInvented citation [generated_report:not-present]."

    monkeypatch.setattr(
        "packages.services.market_dashboard.get_platform_settings",
        lambda: {
            "market_data_provider": "mock",
            "llm_provider": "openai",
            "llm_api_key": "test-key",
            "llm_api_base": "https://example.test/v1",
        },
    )
    monkeypatch.setattr(
        "packages.services.market_dashboard.get_llm_provider",
        lambda _settings=None: FakeDashboardLLMProvider(),
    )

    payload = get_market_overview_payload(
        session=session,
        provider_name="mock",
        today=date(2026, 7, 3),
    )

    dashboard_brief = payload["dashboard_brief"]
    narrative = dashboard_brief["narrative"]
    assert narrative["model"]["used_llm"] is False
    assert narrative["model"]["fallback_reason"] == "LLM citation validation failed: unknown citation id."
    assert "Invented citation" not in narrative["answer_markdown"]
    diagnostics_by_code = {diagnostic["code"]: diagnostic for diagnostic in dashboard_brief["diagnostics"]}
    assert diagnostics_by_code["CITATION_UNKNOWN_ID"]["details"] == {
        "unknown_ids": ["generated_report:not-present"]
    }
    assert diagnostics_by_code["FALLBACK_USED"]["details"] == {
        "reason": "LLM citation validation failed: unknown citation id."
    }


def test_market_overview_keeps_partial_results_when_index_provider_fails(monkeypatch):
    session = make_session()

    def fake_get_bars_payload(symbol, timeframe, start, end, session=None, provider_name=None):
        if symbol == "SPX":
            raise MarketDataProviderUnavailableError("mock", "fetching bars", ConnectionError("down"))
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "source": "mock",
            "provider": "mock",
            "requested_provider": "mock",
            "effective_provider": "mock",
            "status": "ok",
            "no_data_reason": None,
            "items": [
                {"timestamp": "2026-07-02", "open": 100, "high": 103, "low": 99, "close": 101, "volume": 1000},
                {"timestamp": "2026-07-03", "open": 101, "high": 104, "low": 100, "close": 102, "volume": 1100},
            ],
        }

    monkeypatch.setattr(
        "packages.services.market_dashboard.get_bars_payload",
        fake_get_bars_payload,
    )

    payload = get_market_overview_payload(
        session=session,
        provider_name="mock",
        today=date(2026, 7, 3),
    )

    unavailable_indices = [item for item in payload["indices"]["items"] if item["status"] == "unavailable"]
    assert len(unavailable_indices) == 1
    assert unavailable_indices[0]["code"] == "us_sp_500"
    assert payload["followed"]["items"][0]["status"] == "ok"
    assert payload["diagnostics"][0]["section"] == "indices"
    assert payload["diagnostics"][0]["code"] == "us_sp_500"


def test_market_overview_payload_uses_provider_date_cache(monkeypatch):
    session = make_session()
    fake_redis = FakeRedis()
    calls: list[str] = []

    def fake_get_bars_payload(symbol, timeframe, start, end, session=None, provider_name=None):
        calls.append(symbol)
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "source": "mock",
            "provider": "mock",
            "requested_provider": "mock",
            "effective_provider": "mock",
            "status": "ok",
            "no_data_reason": None,
            "items": [
                {"timestamp": "2026-07-02", "open": 100, "high": 103, "low": 99, "close": 101, "volume": 1000},
                {"timestamp": "2026-07-03", "open": 101, "high": 104, "low": 100, "close": 102, "volume": 1100},
            ],
        }

    monkeypatch.setattr("packages.shared.cache.redis_client", fake_redis)
    monkeypatch.setattr("packages.services.market_dashboard.get_bars_payload", fake_get_bars_payload)

    first_payload = get_market_overview_payload(
        session=session,
        provider_name="mock",
        today=date(2026, 7, 3),
    )
    second_payload = get_market_overview_payload(
        session=session,
        provider_name="mock",
        today=date(2026, 7, 3),
    )

    assert second_payload == first_payload
    assert len(calls) == 11
    assert fake_redis.expirations["dashboard:market-overview:mock:2026-07-03"] == 300


def test_market_overview_payload_does_not_cache_contradictory_ok_items(monkeypatch):
    session = make_session()
    fake_redis = FakeRedis()
    calls: list[str] = []

    def fake_get_bars_payload(symbol, timeframe, start, end, session=None, provider_name=None):
        calls.append(symbol)
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "source": "mock",
            "provider": "mock",
            "requested_provider": "mock",
            "effective_provider": "mock",
            "status": "ok",
            "no_data_reason": None,
            "items": [
                {
                    "timestamp": "2026-07-02",
                    "open": 100,
                    "high": 103,
                    "low": 99,
                    "close": 101,
                    "volume": 1000,
                },
                {
                    "timestamp": "2026-07-03",
                    "open": float("nan"),
                    "high": float("nan"),
                    "low": float("nan"),
                    "close": float("nan"),
                    "volume": 1100,
                },
            ],
        }

    monkeypatch.setattr("packages.shared.cache.redis_client", fake_redis)
    monkeypatch.setattr(
        "packages.services.market_dashboard.get_bars_payload",
        fake_get_bars_payload,
    )

    get_market_overview_payload(
        session=session,
        provider_name="mock",
        today=date(2026, 7, 3),
    )
    get_market_overview_payload(
        session=session,
        provider_name="mock",
        today=date(2026, 7, 3),
    )

    assert len(calls) == 22
    assert fake_redis.store == {}


def test_market_overview_payload_caches_explicit_no_data_items(monkeypatch):
    session = make_session()
    fake_redis = FakeRedis()
    calls: list[str] = []

    def fake_get_bars_payload(symbol, timeframe, start, end, session=None, provider_name=None):
        calls.append(symbol)
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "source": "mock",
            "provider": "mock",
            "requested_provider": "mock",
            "effective_provider": "mock",
            "status": "no_data",
            "no_data_reason": "No daily bars were available.",
            "items": [],
        }

    monkeypatch.setattr("packages.shared.cache.redis_client", fake_redis)
    monkeypatch.setattr(
        "packages.services.market_dashboard.get_bars_payload",
        fake_get_bars_payload,
    )

    first_payload = get_market_overview_payload(
        session=session,
        provider_name="mock",
        today=date(2026, 7, 3),
    )
    second_payload = get_market_overview_payload(
        session=session,
        provider_name="mock",
        today=date(2026, 7, 3),
    )

    assert second_payload == first_payload
    assert len(calls) == 11
    assert fake_redis.expirations["dashboard:market-overview:mock:2026-07-03"] == 300


def test_market_overview_cache_failures_do_not_block_payload(monkeypatch):
    session = make_session()
    calls: list[str] = []

    def fake_get_bars_payload(symbol, timeframe, start, end, session=None, provider_name=None):
        calls.append(symbol)
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "source": "mock",
            "provider": "mock",
            "requested_provider": "mock",
            "effective_provider": "mock",
            "status": "ok",
            "no_data_reason": None,
            "items": [
                {"timestamp": "2026-07-02", "open": 100, "high": 103, "low": 99, "close": 101, "volume": 1000},
                {"timestamp": "2026-07-03", "open": 101, "high": 104, "low": 100, "close": 102, "volume": 1100},
            ],
        }

    monkeypatch.setattr("packages.shared.cache.redis_client", FailingRedis())
    monkeypatch.setattr("packages.services.market_dashboard.get_bars_payload", fake_get_bars_payload)

    payload = get_market_overview_payload(
        session=session,
        provider_name="mock",
        today=date(2026, 7, 3),
    )

    assert payload["provider"] == "mock"
    assert payload["followed"]["items"][0]["status"] == "ok"
    assert len(payload["indices"]["items"]) == 10
    assert len(calls) == 11
