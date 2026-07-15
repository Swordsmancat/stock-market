import json
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.ai.market_assistant import (
    MarketAssistantCitation,
    MarketAssistantPromptContext,
    build_market_assistant_prompt,
    build_deterministic_market_answer,
)
from packages.services import market_assistant as market_assistant_service
from packages.services.market_indicators import (
    MarketIndicatorObservationSeed,
    seed_market_indicators,
    upsert_market_indicator_observation,
)
from packages.services.research_source_notes import ResearchSourceNoteInput, create_research_source_note
from packages.shared.database import Base


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def patch_snapshot_test_dependencies(monkeypatch):
    monkeypatch.setattr(
        market_assistant_service,
        "get_bars_payload",
        lambda *args, **kwargs: {
            "symbol": "000001",
            "timeframe": "1d",
            "source": "mock",
            "provider": "mock",
            "requested_provider": "mock",
            "effective_provider": "mock",
            "items": [
                {"timestamp": "2026-07-10", "close": 10.0},
                {"timestamp": "2026-07-11", "close": 10.5},
            ],
        },
    )
    for builder_name in (
        "_build_indicator_context",
        "_build_macro_indicator_context",
        "_build_fundamental_context",
        "_build_news_context",
        "_build_generated_report_context",
        "_build_research_source_note_context",
        "_build_official_disclosure_context",
        "_build_official_disclosure_section_context",
        "_build_market_daily_evidence_context",
    ):
        monkeypatch.setattr(
            market_assistant_service,
            builder_name,
            lambda *args, **kwargs: ("No optional evidence.", []),
        )


def test_deterministic_answer_refuses_direct_trading_instruction():
    context = MarketAssistantPromptContext(
        symbol="AAPL",
        locale="zh",
        question="AAPL 现在能不能买入？",
        timeframe="1d",
        start="2026-01-01",
        end="2026-01-03",
        as_of="2026-01-03",
        latest_close=103.0,
        period_change_pct=1.98,
        bar_count=3,
        price_summary="Daily bars are available.",
        indicator_summary="MA=102",
        fundamental_summary="PE=28.4",
        news_summary="No stored news sentiment is available.",
    )

    answer = build_deterministic_market_answer(context)

    assert "不能给出直接买入、卖出、持有、仓位或目标价指令" in answer
    assert "不构成投资建议" in answer
    assert "AAPL" in answer


def test_market_assistant_returns_traceable_fallback_answer(monkeypatch):
    monkeypatch.setattr(
        market_assistant_service,
        "get_bars_payload",
        lambda *args, **kwargs: {
            "symbol": "AAPL",
            "timeframe": "1d",
            "source": "mock",
            "provider": "mock",
            "requested_provider": "mock",
            "effective_provider": "mock",
            "items": [
                {"timestamp": "2026-01-01", "close": 100.0},
                {"timestamp": "2026-01-03", "close": 105.0},
            ],
        },
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_platform_settings",
        lambda: {"llm_provider": "mock", "llm_api_key": "", "llm_api_base": ""},
    )

    payload = market_assistant_service.answer_market_assistant_question(
        symbol="aapl",
        question="请总结近期走势和风险。",
        start=date(2026, 1, 1),
        end=date(2026, 1, 3),
        provider_name="mock",
        session=None,
    )

    assert payload["status"] == "degraded"
    assert payload["symbol"] == "AAPL"
    assert payload["model"]["used_llm"] is False
    assert payload["context"]["latest_close"] == 105.0
    assert payload["context"]["period_change_pct"] == 5.0
    assert payload["context"]["research_snapshot"] is None
    assert payload["citations"][0]["id"] == "bars_1d:AAPL:2026-01-03"
    assert payload["citations"][0]["source_type"] == "bars"
    assert payload["safety"]["not_investment_advice"] is True
    assert "不构成投资建议" in payload["answer_markdown"]


def test_market_assistant_uses_cn_fallback_bars_and_effective_provider(monkeypatch):
    patch_snapshot_test_dependencies(monkeypatch)
    captured: dict[str, object] = {}

    def bars_stub(*args, **kwargs):
        captured.update(kwargs)
        return {
            "symbol": "600519",
            "market": "CN",
            "timeframe": "1d",
            "source": "akshare.stock_zh_a_daily",
            "provider": "akshare",
            "requested_provider": "yfinance",
            "effective_provider": "akshare",
            "adjustment": "qfq",
            "fallback_used": True,
            "source_attempts": [
                {
                    "provider": "yfinance",
                    "source": "yfinance.fetch_bars",
                    "status": "no_data",
                    "row_count": 0,
                },
                {
                    "provider": "akshare",
                    "source": "akshare.stock_zh_a_daily",
                    "status": "selected",
                    "row_count": 2,
                },
            ],
            "items": [
                {"timestamp": "2026-07-08", "close": 1490.0},
                {"timestamp": "2026-07-09", "close": 1495.0},
            ],
        }

    monkeypatch.setattr(market_assistant_service, "get_bars_payload", bars_stub)
    monkeypatch.setattr(
        market_assistant_service,
        "get_platform_settings",
        lambda: {"llm_provider": "mock", "llm_api_key": "", "llm_api_base": ""},
    )

    payload = market_assistant_service.answer_market_assistant_question(
        symbol="600519",
        question="Summarize the verified daily evidence.",
        locale="en",
        start=date(2026, 7, 1),
        end=date(2026, 7, 10),
        provider_name="yfinance",
        market="CN",
        session=None,
    )

    assert captured["market"] == "CN"
    assert payload["context"]["market"] == "CN"
    assert payload["context"]["effective_provider"] == "akshare"
    assert payload["context"]["source"] == "akshare.stock_zh_a_daily"
    assert payload["context"]["fallback_used"] is True
    assert payload["citations"][0]["provider"] == "akshare"
    assert not any(
        diagnostic.get("source") == "bars_1d" and diagnostic.get("code") == "SOURCE_NO_DATA"
        for diagnostic in payload["diagnostics"]
    )


def test_market_assistant_preserves_partial_database_bar_diagnostic(monkeypatch):
    patch_snapshot_test_dependencies(monkeypatch)
    monkeypatch.setattr(
        market_assistant_service,
        "get_bars_payload",
        lambda *args, **kwargs: {
            "symbol": "600519",
            "market": "CN",
            "timeframe": "1d",
            "source": "database",
            "provider": "akshare",
            "requested_provider": "yfinance",
            "effective_provider": "akshare",
            "upstream_source": "akshare.stock_zh_a_hist",
            "adjustment": "qfq",
            "status": "degraded",
            "diagnostics": [
                {
                    "source": "database",
                    "status": "degraded",
                    "code": "MIXED_DAILY_BAR_PROVENANCE",
                    "message": "Stored daily bars span multiple provenance cohorts; only the latest coherent cohort was returned.",
                    "dropped_row_count": 9,
                }
            ],
            "items": [{"timestamp": "2026-07-09", "close": 1495.0}],
        },
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_platform_settings",
        lambda: {"llm_provider": "mock", "llm_api_key": "", "llm_api_base": ""},
    )

    payload = market_assistant_service.answer_market_assistant_question(
        symbol="600519",
        question="Summarize the verified daily evidence.",
        locale="en",
        start=date(2026, 7, 1),
        end=date(2026, 7, 10),
        provider_name="yfinance",
        market="CN",
        session=None,
    )

    diagnostic = next(
        item
        for item in payload["diagnostics"]
        if item.get("code") == "MIXED_DAILY_BAR_PROVENANCE"
    )
    assert payload["status"] == "degraded"
    assert payload["context"]["bars_status"] == "degraded"
    assert payload["context"]["bar_count"] == 1
    assert diagnostic["dropped_row_count"] == 9


def test_market_assistant_reports_configured_physical_model(monkeypatch):
    class FakeProvider:
        def generate(self, prompt: str) -> str:
            assert "bars_1d:AAPL:2026-01-03" in prompt
            return "### Summary\nAAPL rose over the period. [bars_1d:AAPL:2026-01-03]"

    monkeypatch.setattr(
        market_assistant_service,
        "get_bars_payload",
        lambda *args, **kwargs: {
            "symbol": "AAPL",
            "timeframe": "1d",
            "source": "mock",
            "provider": "mock",
            "requested_provider": "mock",
            "effective_provider": "mock",
            "items": [
                {"timestamp": "2026-01-01", "close": 100.0},
                {"timestamp": "2026-01-03", "close": 105.0},
            ],
        },
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_platform_settings",
        lambda: {
            "llm_provider": "openai",
            "llm_api_key": "configured",
            "llm_model": "  deepseek-chat  ",
        },
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_llm_provider",
        lambda _settings=None: FakeProvider(),
    )

    payload = market_assistant_service.answer_market_assistant_question(
        symbol="AAPL",
        question="What changed recently?",
        locale="en",
        start=date(2026, 1, 1),
        end=date(2026, 1, 3),
        provider_name="mock",
        session=None,
    )

    assert payload["model"] == {
        "provider": "openai",
        "name": "deepseek-chat",
        "used_llm": True,
        "fallback_reason": None,
    }
    assert payload["citations"][0]["id"] == "bars_1d:AAPL:2026-01-03"


def test_market_assistant_citation_payload_keeps_old_fields_and_optional_metadata():
    citation = MarketAssistantCitation(
        id="news:AAPL:2026-01-03:abc123",
        label="News for AAPL",
        source="news",
        url="https://example.com/aapl",
        source_type="news",
        as_of="2026-01-03T12:00:00+00:00",
        provider="mock_news",
        excerpt="Apple expands services revenue.",
        metadata={"sentiment": "positive"},
    )

    payload = citation.to_payload()

    assert payload["id"] == "news:AAPL:2026-01-03:abc123"
    assert payload["label"] == "News for AAPL"
    assert payload["source"] == "news"
    assert payload["url"] == "https://example.com/aapl"
    assert payload["source_type"] == "news"
    assert payload["metadata"] == {"sentiment": "positive"}


def test_market_assistant_prompt_requires_known_inline_citation_ids():
    context = MarketAssistantPromptContext(
        symbol="AAPL",
        locale="en",
        question="What changed recently?",
        timeframe="1d",
        start="2026-01-01",
        end="2026-01-03",
        as_of="2026-01-03",
        latest_close=105.0,
        period_change_pct=5.0,
        bar_count=2,
        price_summary="Daily bars are available.",
        indicator_summary="MA=104",
        fundamental_summary="PE=28.4",
        news_summary="Recent services news.",
        research_summary="Generated daily report available.",
        citations=[
            MarketAssistantCitation(
                id="bars_1d:AAPL:2026-01-03",
                label="Daily bars for AAPL as of 2026-01-03",
                source="bars_1d",
            )
        ],
    )

    prompt = build_market_assistant_prompt(context)

    assert "bars_1d:AAPL:2026-01-03" in prompt
    assert "Macro context:" in prompt
    assert "Use inline citation IDs in square brackets" in prompt
    assert "use only citation IDs listed above" in prompt


def test_market_assistant_includes_citable_macro_indicator_observations(monkeypatch):
    session = make_session()
    seed_market_indicators(session=session)
    upsert_market_indicator_observation(
        MarketIndicatorObservationSeed(
            code="buffett_indicator_us",
            as_of=date(2026, 1, 2),
            value=Decimal("188.5"),
            source="Audited seed: World Bank market cap and GDP",
            components={
                "source_url": "https://data.worldbank.org/indicator/CM.MKT.LCAP.GD.ZS",
                "calculation": "Market capitalization divided by GDP.",
                "review_note": "Reviewed for assistant macro context.",
            },
        ),
        session=session,
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_bars_payload",
        lambda *args, **kwargs: {
            "symbol": "AAPL",
            "timeframe": "1d",
            "source": "mock",
            "provider": "mock",
            "requested_provider": "mock",
            "effective_provider": "mock",
            "items": [
                {"timestamp": "2026-01-01", "close": 100.0},
                {"timestamp": "2026-01-03", "close": 105.0},
            ],
        },
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_platform_settings",
        lambda: {
            "llm_provider": "mock",
            "llm_api_key": "",
            "llm_api_base": "",
            "favorite_macro_indicator_codes": ["buffett_indicator_us", "us_10y_yield"],
        },
    )

    payload = market_assistant_service.answer_market_assistant_question(
        symbol="AAPL",
        question="Summarize macro context.",
        locale="en",
        start=date(2026, 1, 1),
        end=date(2026, 1, 3),
        provider_name="mock",
        session=session,
    )

    citations_by_id = {citation["id"]: citation for citation in payload["citations"]}
    macro_citation = citations_by_id["market_indicator:buffett_indicator_us:2026-01-02"]
    assert macro_citation["source"] == "market_indicators"
    assert macro_citation["source_type"] == "macro_indicator"
    assert macro_citation["metadata"]["code"] == "buffett_indicator_us"
    assert macro_citation["metadata"]["components"]["calculation"] == "Market capitalization divided by GDP."
    assert "Buffett Indicator - United States=188.5%" in payload["context"]["macro_summary"]
    assert "Buffett Indicator - United States=188.5%" in payload["answer_markdown"]
    assert any(diagnostic.get("code") == "MACRO_INDICATOR_NO_DATA" for diagnostic in payload["diagnostics"])


def test_market_assistant_reports_missing_macro_observations_without_citations(monkeypatch):
    session = make_session()
    seed_market_indicators(session=session)
    monkeypatch.setattr(
        market_assistant_service,
        "get_bars_payload",
        lambda *args, **kwargs: {
            "symbol": "AAPL",
            "timeframe": "1d",
            "source": "mock",
            "provider": "mock",
            "requested_provider": "mock",
            "effective_provider": "mock",
            "items": [
                {"timestamp": "2026-01-01", "close": 100.0},
                {"timestamp": "2026-01-03", "close": 105.0},
            ],
        },
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_platform_settings",
        lambda: {"llm_provider": "mock", "llm_api_key": "", "llm_api_base": ""},
    )

    payload = market_assistant_service.answer_market_assistant_question(
        symbol="AAPL",
        question="Summarize macro context.",
        locale="en",
        start=date(2026, 1, 1),
        end=date(2026, 1, 3),
        provider_name="mock",
        session=session,
    )

    assert payload["context"]["macro_summary"] == "No stored macro indicator observations are available."
    assert not any(citation.get("id", "").startswith("market_indicator:") for citation in payload["citations"])
    assert any(diagnostic.get("code") == "MACRO_INDICATOR_NO_DATA" for diagnostic in payload["diagnostics"])


def test_market_assistant_generates_research_evidence_citations_for_available_sources(monkeypatch):
    news_requests: list[tuple[str, str | None]] = []

    def fake_news_payload(symbol, session, *, market):
        news_requests.append((symbol, market))
        return {
            "symbol": symbol,
            "source": "database",
            "summary": {"latest_sentiment": "positive", "article_count": 1},
            "items": [
                {
                    "title": "Apple expands services revenue",
                    "url": "https://example.com/aapl-services",
                    "source": "mock_news",
                    "published_at": "2026-01-03T12:00:00+00:00",
                    "summary": "Apple expands services revenue in the quarter.",
                    "sentiment": "positive",
                    "confidence": 0.91,
                }
            ],
        }

    monkeypatch.setattr(
        market_assistant_service,
        "get_bars_payload",
        lambda *args, **kwargs: {
            "symbol": "AAPL",
            "timeframe": "1d",
            "source": "mock",
            "provider": "mock",
            "requested_provider": "mock",
            "effective_provider": "mock",
            "items": [
                {"timestamp": "2026-01-01", "close": 100.0},
                {"timestamp": "2026-01-03", "close": 105.0},
            ],
        },
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_stored_indicators_payload",
        lambda symbol, session: {
            "symbol": symbol,
            "source": "database",
            "as_of": "2026-01-03T00:00:00+00:00",
            "indicators": {"ma": 104.0, "rsi": 55.0},
        },
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_fundamental_payload",
        lambda symbol, as_of=None, session=None: {
            "symbol": symbol,
            "source": "database",
            "as_of": "2026-01-03",
            "item": {
                "currency": "USD",
                "pe_ratio": 28.4,
                "revenue_growth": 0.08,
                "net_margin": 0.24,
                "debt_to_assets": 0.31,
            },
            "citation": "fundamental_metrics:AAPL:2026-01-03",
        },
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_news_sentiment_payload",
        fake_news_payload,
    )
    monkeypatch.setattr(
        market_assistant_service,
        "list_reports_payload",
        lambda *args, **kwargs: {
            "source": "database",
            "total": 1,
            "items": [
                {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "symbol": "AAPL",
                    "report_type": "daily",
                    "as_of": "2026-01-03",
                    "content_markdown": "# AAPL report\nServices revenue increased.",
                    "citations": ["bars_1d:AAPL:2026-01-03"],
                    "source_summary": {"source": "database"},
                    "task_run_id": None,
                    "created_at": "2026-01-03T13:00:00+00:00",
                }
            ],
        },
    )
    monkeypatch.setattr(
        market_assistant_service,
        "list_citable_research_source_note_citations",
        lambda *args, **kwargs: [
            {
                "id": "research_source_note:11111111-2222-3333-4444-555555555555",
                "label": "AAPL reviewed source note",
                "source": "research_source_notes",
                "source_type": "research_source_note",
                "url": "https://example.com/aapl-source",
                "as_of": "2026-01-03",
                "provider": "Manual research notebook",
                "retrieved_at": "2026-01-03T13:30:00+00:00",
                "excerpt": "Reviewed notebook excerpt for AAPL.",
                "metadata": {"symbols": ["AAPL"], "tags": ["valuation"]},
            }
        ],
    )
    monkeypatch.setattr(
        market_assistant_service,
        "list_citable_market_daily_evidence_citations",
        lambda *args, **kwargs: [
            {
                "id": "market_daily_event:hot_sector:semiconductor:2026-01-03",
                "label": "Hot sector: Semiconductor",
                "source": "market_daily_evidence",
                "source_type": "market_daily_event",
                "as_of": "2026-01-03",
                "provider": "fake",
                "retrieved_at": "2026-01-03T13:45:00+00:00",
                "excerpt": "Semiconductor sector fund-flow context is stored locally.",
                "metadata": {"event_type": "hot_sector", "market": "CN"},
            }
        ],
    )
    monkeypatch.setattr(
        market_assistant_service,
        "list_citable_official_disclosure_citations",
        lambda *args, **kwargs: [
            {
                "id": "official_disclosure:11111111-3333-3333-4444-555555555555",
                "label": "AAPL annual report publication",
                "source": "official_disclosures",
                "source_type": "official_disclosure",
                "url": "https://www.cninfo.com.cn/new/disclosure/detail?announcementId=1",
                "as_of": "2026-01-03T12:00:00+00:00",
                "provider": "cninfo",
                "retrieved_at": "2026-01-03T13:50:00+00:00",
                "excerpt": "CNINFO published disclosure metadata; document body has not been ingested.",
                "metadata": {"evidence_scope": "metadata_only", "content_ingested": False},
            }
        ],
    )
    monkeypatch.setattr(
        market_assistant_service,
        "list_citable_official_disclosure_section_citations",
        lambda *args, **kwargs: [
            {
                "id": "official_disclosure_section:11111111-4444-3333-4444-555555555555",
                "label": "AAPL annual report — Risk Factors",
                "source": "official_disclosure_sections",
                "source_type": "official_disclosure_section",
                "url": "https://static.cninfo.com.cn/finalpage/2026-01-03/1.PDF",
                "as_of": "2026-01-03T12:00:00+00:00",
                "provider": "cninfo",
                "retrieved_at": "2026-01-03T13:55:00+00:00",
                "excerpt": "Customer concentration is a material risk.",
                "metadata": {
                    "evidence_scope": "document_section",
                    "content_ingested": True,
                    "page_number": 12,
                    "document_sha256": "a" * 64,
                },
            }
        ],
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_platform_settings",
        lambda: {"llm_provider": "mock", "llm_api_key": "", "llm_api_base": ""},
    )

    payload = market_assistant_service.answer_market_assistant_question(
        symbol="AAPL",
        question="请总结近期研究资料。",
        start=date(2026, 1, 1),
        end=date(2026, 1, 3),
        provider_name="mock",
        market="US",
        session=object(),
    )

    citations_by_source_type = {citation.get("source_type"): citation for citation in payload["citations"]}
    assert "bars" in citations_by_source_type
    assert "technical_indicator" in citations_by_source_type
    assert "fundamental" in citations_by_source_type
    assert "news" in citations_by_source_type
    assert "generated_report" in citations_by_source_type
    assert "research_source_note" in citations_by_source_type
    assert "market_daily_event" in citations_by_source_type
    assert "official_disclosure" in citations_by_source_type
    assert "official_disclosure_section" in citations_by_source_type
    assert citations_by_source_type["news"]["url"] == "https://example.com/aapl-services"
    assert news_requests == [("AAPL", "US")]
    assert citations_by_source_type["generated_report"]["id"] == "generated_report:11111111-1111-1111-1111-111111111111"
    assert citations_by_source_type["research_source_note"]["id"].startswith("research_source_note:")
    assert "Reviewed source notebook entries available" in payload["context"]["research_summary"]
    assert "document bodies not ingested" in payload["context"]["research_summary"]
    assert "page-anchored excerpts" in payload["context"]["research_summary"]
    assert "Stored market daily evidence available" in payload["context"]["market_daily_summary"]


def test_market_assistant_includes_only_reviewed_citable_source_notes(monkeypatch):
    session = make_session()
    citable_note = create_research_source_note(
        ResearchSourceNoteInput(
            title="AAPL reviewed citable source",
            source_name="Manual notebook",
            source_type="valuation_component",
            source_url="https://example.com/aapl-citable",
            symbols=["AAPL"],
            excerpt="Reviewed citable excerpt.",
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
            title="AAPL draft source",
            source_name="Manual notebook",
            source_type="valuation_component",
            source_url="https://example.com/aapl-draft",
            symbols=["AAPL"],
            excerpt="Draft excerpt.",
            review_status="draft",
            is_citable=False,
        ),
        session=session,
    )
    create_research_source_note(
        ResearchSourceNoteInput(
            title="AAPL reviewed collection source",
            source_name="Manual notebook",
            source_type="valuation_component",
            source_url="https://example.com/aapl-reviewed-collection",
            symbols=["AAPL"],
            excerpt="Reviewed but not citable excerpt.",
            review_status="reviewed",
            is_citable=False,
        ),
        session=session,
    )

    monkeypatch.setattr(
        market_assistant_service,
        "get_bars_payload",
        lambda *args, **kwargs: {
            "symbol": "AAPL",
            "timeframe": "1d",
            "source": "mock",
            "provider": "mock",
            "requested_provider": "mock",
            "effective_provider": "mock",
            "items": [
                {"timestamp": "2026-01-01", "close": 100.0},
                {"timestamp": "2026-01-03", "close": 105.0},
            ],
        },
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_stored_indicators_payload",
        lambda symbol, session: {
            "symbol": symbol,
            "source": "database",
            "as_of": None,
            "indicators": {},
        },
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_fundamental_payload",
        lambda symbol, as_of=None, session=None: {"symbol": symbol, "source": "database", "item": None},
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_news_sentiment_payload",
        lambda symbol, session: {"symbol": symbol, "source": "database", "summary": {}, "items": []},
    )
    monkeypatch.setattr(
        market_assistant_service,
        "list_reports_payload",
        lambda *args, **kwargs: {"source": "database", "total": 0, "items": []},
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_platform_settings",
        lambda: {"llm_provider": "mock", "llm_api_key": "", "llm_api_base": ""},
    )

    payload = market_assistant_service.answer_market_assistant_question(
        symbol="AAPL",
        question="Summarize source notebook context.",
        locale="en",
        start=date(2026, 1, 1),
        end=date(2026, 1, 3),
        provider_name="mock",
        session=session,
    )

    citation_ids = {citation["id"] for citation in payload["citations"]}
    citation_labels = {citation["label"] for citation in payload["citations"]}
    assert citable_note["citation_id"] in citation_ids
    source_note_citation = next(
        citation for citation in payload["citations"] if citation["id"] == citable_note["citation_id"]
    )
    assert source_note_citation["metadata"]["source_id"] == "buffett_manual_valuation_components"
    assert source_note_citation["metadata"]["target_indicator_codes"] == ["buffett_indicator_us"]
    assert source_note_citation["metadata"]["component_role"] == "market_cap"
    assert source_note_citation["metadata"]["completeness"]["status"] == "partial"
    assert "AAPL draft source" not in citation_labels
    assert "AAPL reviewed collection source" not in citation_labels


def test_market_assistant_recognizes_invented_disclosure_section_citation_ids():
    unknown = market_assistant_service._extract_unknown_inline_citation_ids(
        "Unsupported claim [official_disclosure_section:not-present].",
        [],
    )

    assert unknown == ["official_disclosure_section:not-present"]

    shortlist_unknown = market_assistant_service._extract_unknown_inline_citation_ids(
        "Unsupported claim [research_shortlist:not-present].",
        [],
    )

    assert shortlist_unknown == ["research_shortlist:not-present"]


def test_market_assistant_detects_unknown_llm_citation_ids(monkeypatch):
    class HallucinatingProvider:
        def generate(self, prompt: str) -> str:
            return "### Summary\nUnsupported claim [market_daily_event:hot_sector:invented:2026-01-03]."

    monkeypatch.setattr(
        market_assistant_service,
        "get_bars_payload",
        lambda *args, **kwargs: {
            "symbol": "AAPL",
            "timeframe": "1d",
            "source": "mock",
            "provider": "mock",
            "requested_provider": "mock",
            "effective_provider": "mock",
            "items": [
                {"timestamp": "2026-01-01", "close": 100.0},
                {"timestamp": "2026-01-03", "close": 105.0},
            ],
        },
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_platform_settings",
        lambda: {"llm_provider": "openai", "llm_api_key": "configured", "llm_api_base": ""},
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_llm_provider",
        lambda _settings=None: HallucinatingProvider(),
    )

    payload = market_assistant_service.answer_market_assistant_question(
        symbol="AAPL",
        question="What changed recently?",
        locale="en",
        start=date(2026, 1, 1),
        end=date(2026, 1, 3),
        provider_name="mock",
        session=None,
    )

    assert payload["status"] == "degraded"
    assert payload["model"]["used_llm"] is False
    assert payload["model"]["fallback_reason"] == "LLM citation validation failed: unknown citation id."
    citation_diagnostic = next(
        diagnostic for diagnostic in payload["diagnostics"] if diagnostic.get("code") == "CITATION_UNKNOWN_ID"
    )
    assert citation_diagnostic["details"]["unknown_ids"] == [
        "market_daily_event:hot_sector:invented:2026-01-03"
    ]


def test_market_assistant_detects_unknown_macro_indicator_llm_citation_ids(monkeypatch):
    class HallucinatingProvider:
        def generate(self, prompt: str) -> str:
            return "### Summary\nUnsupported macro claim [market_indicator:buffett_indicator_us:2026-01-02]."

    monkeypatch.setattr(
        market_assistant_service,
        "get_bars_payload",
        lambda *args, **kwargs: {
            "symbol": "AAPL",
            "timeframe": "1d",
            "source": "mock",
            "provider": "mock",
            "requested_provider": "mock",
            "effective_provider": "mock",
            "items": [
                {"timestamp": "2026-01-01", "close": 100.0},
                {"timestamp": "2026-01-03", "close": 105.0},
            ],
        },
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_platform_settings",
        lambda: {"llm_provider": "openai", "llm_api_key": "configured", "llm_api_base": ""},
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_llm_provider",
        lambda _settings=None: HallucinatingProvider(),
    )

    payload = market_assistant_service.answer_market_assistant_question(
        symbol="AAPL",
        question="What changed recently?",
        locale="en",
        start=date(2026, 1, 1),
        end=date(2026, 1, 3),
        provider_name="mock",
        session=None,
    )

    assert payload["status"] == "degraded"
    assert payload["model"]["used_llm"] is False
    assert payload["model"]["fallback_reason"] == "LLM citation validation failed: unknown citation id."
    citation_diagnostic = next(
        diagnostic for diagnostic in payload["diagnostics"] if diagnostic.get("code") == "CITATION_UNKNOWN_ID"
    )
    assert citation_diagnostic["details"]["unknown_ids"] == ["market_indicator:buffett_indicator_us:2026-01-02"]


def test_market_assistant_returns_no_data_without_llm(monkeypatch):
    class UnexpectedProvider:
        def generate(self, prompt: str) -> str:
            raise AssertionError("LLM should not be called when no verified bars exist.")

    monkeypatch.setattr(
        market_assistant_service,
        "get_bars_payload",
        lambda *args, **kwargs: {
            "symbol": "AAPL",
            "timeframe": "1d",
            "source": "mock",
            "provider": "mock",
            "requested_provider": "mock",
            "effective_provider": "mock",
            "items": [],
        },
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_platform_settings",
        lambda: {"llm_provider": "openai", "llm_api_key": "configured", "llm_api_base": ""},
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_llm_provider",
        lambda _settings=None: UnexpectedProvider(),
    )

    payload = market_assistant_service.answer_market_assistant_question(
        symbol="AAPL",
        question="请分析走势。",
        start=date(2026, 1, 1),
        end=date(2026, 1, 2),
        provider_name="mock",
        session=None,
    )

    assert payload["status"] == "no_data"
    assert payload["model"]["used_llm"] is False
    assert payload["context"]["bar_count"] == 0
    assert payload["context"]["research_snapshot"] is None
    assert payload["citations"] == []
    assert payload["diagnostics"][0]["source"] == "bars_1d"
    assert "没有获取到" in payload["answer_markdown"]


def test_market_assistant_preserves_degraded_daily_source_exhaustion(monkeypatch):
    class UnexpectedProvider:
        def generate(self, prompt: str) -> str:
            raise AssertionError("LLM should not be called when daily sources are unavailable.")

    no_data_reason = "No daily bars were available for the requested symbol/date range."
    monkeypatch.setattr(
        market_assistant_service,
        "get_bars_payload",
        lambda *args, **kwargs: {
            "symbol": "600519",
            "market": "CN",
            "timeframe": "1d",
            "source": "none",
            "provider": "yfinance",
            "requested_provider": "yfinance",
            "effective_provider": "yfinance",
            "fallback_used": False,
            "source_attempts": [
                {
                    "provider": "yfinance",
                    "source": "yfinance.fetch_bars",
                    "status": "failed",
                    "exception_type": "TimeoutError",
                }
            ],
            "status": "degraded",
            "no_data_reason": no_data_reason,
            "items": [],
        },
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_platform_settings",
        lambda: {"llm_provider": "openai", "llm_api_key": "configured", "llm_api_base": ""},
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_llm_provider",
        lambda _settings=None: UnexpectedProvider(),
    )

    payload = market_assistant_service.answer_market_assistant_question(
        symbol="600519",
        question="Summarize the verified daily evidence.",
        locale="en",
        start=date(2026, 7, 1),
        end=date(2026, 7, 10),
        provider_name="yfinance",
        market="CN",
        session=None,
    )

    assert payload["status"] == "degraded"
    assert payload["model"]["used_llm"] is False
    assert payload["context"]["bars_status"] == "degraded"
    assert payload["context"]["bars_no_data_reason"] == no_data_reason
    assert payload["context"]["source_attempts"][0] == {
        "provider": "yfinance",
        "source": "yfinance.fetch_bars",
        "status": "failed",
        "exception_type": "TimeoutError",
    }
    assert payload["diagnostics"][0]["status"] == "unavailable"
    assert payload["diagnostics"][0]["code"] == "SOURCE_UNAVAILABLE"


def test_market_assistant_falls_back_when_llm_generation_fails(monkeypatch):
    class FailingProvider:
        def generate(self, prompt: str) -> str:
            raise RuntimeError("upstream unavailable token=secret")

    monkeypatch.setattr(
        market_assistant_service,
        "get_bars_payload",
        lambda *args, **kwargs: {
            "symbol": "AAPL",
            "timeframe": "1d",
            "source": "mock",
            "provider": "mock",
            "requested_provider": "mock",
            "effective_provider": "mock",
            "items": [
                {"timestamp": "2026-01-01", "close": 100.0},
                {"timestamp": "2026-01-02", "close": 99.0},
            ],
        },
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_platform_settings",
        lambda: {"llm_provider": "openai", "llm_api_key": "configured", "llm_api_base": ""},
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_llm_provider",
        lambda _settings=None: FailingProvider(),
    )

    payload = market_assistant_service.answer_market_assistant_question(
        symbol="AAPL",
        question="What changed recently?",
        locale="en",
        start=date(2026, 1, 1),
        end=date(2026, 1, 2),
        provider_name="mock",
        session=None,
    )

    assert payload["status"] == "degraded"
    assert payload["model"]["used_llm"] is False
    assert payload["model"]["fallback_reason"] == "LLM generation failed: RuntimeError."
    assert "secret" not in payload["model"]["fallback_reason"]
    assert "not investment advice" in payload["answer_markdown"]


def test_market_assistant_applies_structured_research_snapshot_without_persisted_prose(
    monkeypatch,
):
    run_id = "11111111-1111-1111-1111-111111111111"
    candidate_id = "22222222-2222-2222-2222-222222222222"
    citation_id = f"research_shortlist:{run_id}:{candidate_id}"
    session = object()
    captured_prompts: list[str] = []

    class SnapshotAwareProvider:
        def generate(self, prompt: str) -> str:
            captured_prompts.append(prompt)
            return f"### Summary\nStructured snapshot applied. [{citation_id}]"

    patch_snapshot_test_dependencies(monkeypatch)
    monkeypatch.setattr(
        market_assistant_service,
        "get_research_shortlist",
        lambda requested_id, *, session: _snapshot_payload_for_test(
            requested_id,
            session,
            expected_run_id=run_id,
            expected_session=session_token,
            candidate_id=candidate_id,
        ),
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_platform_settings",
        lambda: {
            "llm_provider": "openai",
            "llm_api_key": "configured",
            "llm_model": "deepseek-chat",
        },
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_llm_provider",
        lambda _settings=None: SnapshotAwareProvider(),
    )
    session_token = session

    payload = market_assistant_service.answer_market_assistant_question(
        symbol="000001",
        question="Summarize the candidate evidence.",
        locale="en",
        start=date(2026, 7, 10),
        end=date(2026, 7, 11),
        provider_name="mock",
        research_snapshot_id=run_id,
        session=session,
    )

    assert payload["status"] == "ok"
    assert payload["context"]["research_snapshot"] == {
        "requested_id": run_id,
        "status": "applied",
        "applied": True,
        "run_id": run_id,
        "candidate_id": candidate_id,
        "decision_date": "2026-07-11",
        "rank": 2,
        "score": 0.8123,
        "citation_id": citation_id,
    }
    snapshot_citation = next(
        citation
        for citation in payload["citations"]
        if citation["source"] == "research_shortlist"
    )
    structured_evidence = snapshot_citation["metadata"]["structured_evidence"]
    assert structured_evidence == {
        "decision_date": "2026-07-11",
        "rank": 2,
        "score": 0.8123,
        "supporting_factors": [
            {
                "code": "min_net_margin",
                "field": "net_margin",
                "actual": 0.22,
                "threshold": 0.15,
                "buffer": 0.85,
                "dimension": "fundamental",
            }
        ],
        "opposing_factors": [
            {
                "code": "max_pe_ratio",
                "field": "pe_ratio",
                "actual": 19.0,
                "threshold": 20.0,
                "buffer": 0.55,
                "dimension": "fundamental",
            }
        ],
        "data_gaps": [
            {
                "source": "news_sentiment",
                "code": "NEWS_NOT_EVALUATED_BY_PROFILE",
                "status": "not_evaluated",
            }
        ],
        "invalidation_conditions": [
            {
                "rule": "min_net_margin",
                "field": "net_margin",
                "invalidates_when": "less_than",
                "operator": "<",
                "threshold": 0.15,
                "entry_actual": 0.22,
            }
        ],
    }
    assert snapshot_citation["id"] == citation_id

    serialized_output = json.dumps(payload, sort_keys=True)
    prompt = captured_prompts[0]
    for structured_key in (
        "supporting_factors",
        "opposing_factors",
        "data_gaps",
        "invalidation_conditions",
    ):
        assert structured_key in prompt
    for persisted_prose in (
        "LEAK_RUN_EXPLANATION",
        "LEAK_FACTOR_MESSAGE",
        "LEAK_FACTOR_LABEL",
        "LEAK_GAP_MESSAGE",
        "LEAK_INVALIDATION_MESSAGE",
        "LEAK_CANDIDATE_EXPLANATION",
    ):
        assert persisted_prose not in prompt
        assert persisted_prose not in serialized_output


def _snapshot_payload_for_test(
    requested_id: str,
    session: object,
    *,
    expected_run_id: str,
    expected_session: object,
    candidate_id: str,
) -> dict[str, object]:
    assert requested_id == expected_run_id
    assert session is expected_session
    return {
        "status": "ok",
        "run": {
            "id": expected_run_id,
            "decision_date": "2026-07-11",
            "explanation_markdown": "LEAK_RUN_EXPLANATION",
        },
        "items": [
            {
                "id": candidate_id,
                "symbol": "000001",
                "rank": 2,
                "score": 0.8123,
                "supporting_factors": [
                    {
                        "code": "min_net_margin",
                        "field": "net_margin",
                        "actual": 0.22,
                        "threshold": 0.15,
                        "buffer": 0.85,
                        "dimension": "fundamental",
                        "message": "LEAK_FACTOR_MESSAGE",
                        "label": "LEAK_FACTOR_LABEL",
                    }
                ],
                "opposing_factors": [
                    {
                        "code": "max_pe_ratio",
                        "field": "pe_ratio",
                        "actual": 19.0,
                        "threshold": 20.0,
                        "buffer": 0.55,
                        "dimension": "fundamental",
                        "message": "LEAK_FACTOR_MESSAGE",
                    }
                ],
                "data_gaps": [
                    {
                        "source": "news_sentiment",
                        "code": "NEWS_NOT_EVALUATED_BY_PROFILE",
                        "status": "not_evaluated",
                        "message": "LEAK_GAP_MESSAGE",
                    }
                ],
                "invalidation_conditions": [
                    {
                        "rule": "min_net_margin",
                        "field": "net_margin",
                        "invalidates_when": "less_than",
                        "operator": "<",
                        "threshold": 0.15,
                        "entry_actual": 0.22,
                        "message": "LEAK_INVALIDATION_MESSAGE",
                    }
                ],
                "explanation": "LEAK_CANDIDATE_EXPLANATION",
            }
        ],
    }


def test_market_assistant_localizes_applied_snapshot_context_for_chinese_fallback(
    monkeypatch,
):
    run_id = "66666666-6666-6666-6666-666666666666"
    candidate_id = "77777777-7777-7777-7777-777777777777"
    session = object()
    patch_snapshot_test_dependencies(monkeypatch)
    monkeypatch.setattr(
        market_assistant_service,
        "get_research_shortlist",
        lambda requested_id, *, session: _snapshot_payload_for_test(
            requested_id,
            session,
            expected_run_id=run_id,
            expected_session=session_token,
            candidate_id=candidate_id,
        ),
    )
    monkeypatch.setattr(
        market_assistant_service,
        "get_platform_settings",
        lambda: {"llm_provider": "mock", "llm_api_key": ""},
    )
    session_token = session

    payload = market_assistant_service.answer_market_assistant_question(
        symbol="000001",
        question="请总结候选证据。",
        locale="zh",
        start=date(2026, 7, 10),
        end=date(2026, 7, 11),
        provider_name="mock",
        research_snapshot_id=run_id,
        session=session,
    )

    snapshot_citation = next(
        citation
        for citation in payload["citations"]
        if citation["source"] == "research_shortlist"
    )
    serialized_output = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    assert payload["model"]["used_llm"] is False
    assert snapshot_citation["label"] == "000001 的已提交每日候选快照（2026-07-11）"
    assert "已应用已提交的每日候选快照结构化证据" in snapshot_citation["excerpt"]
    assert "已应用已提交的每日候选快照结构化证据" in payload["answer_markdown"]
    assert "Committed research shortlist snapshot evidence" not in serialized_output


def test_market_assistant_degrades_explicitly_for_unapplied_research_snapshots(
    monkeypatch,
):
    session = object()
    missing_id = "33333333-3333-3333-3333-333333333333"
    mismatch_id = "44444444-4444-4444-4444-444444444444"
    session_unavailable_id = "55555555-5555-5555-5555-555555555555"
    lookup_ids: list[str] = []

    def get_snapshot_stub(requested_id: str, *, session: object):
        lookup_ids.append(requested_id)
        if requested_id == missing_id:
            return None
        assert requested_id == mismatch_id
        return {
            "status": "ok",
            "run": {"id": mismatch_id, "decision_date": "2026-07-11"},
            "items": [{"symbol": "000002"}],
        }

    patch_snapshot_test_dependencies(monkeypatch)
    monkeypatch.setattr(
        market_assistant_service,
        "get_research_shortlist",
        get_snapshot_stub,
    )
    monkeypatch.setattr(
        market_assistant_service,
        "_generate_answer_or_fallback",
        lambda prompt_context: (
            "### Summary\nNo snapshot evidence was applied.",
            {
                "provider": "openai",
                "name": "test-model",
                "used_llm": True,
                "fallback_reason": None,
            },
        ),
    )

    cases = (
        ("not-a-uuid", session, "invalid", "RESEARCH_SNAPSHOT_INVALID_ID"),
        (
            session_unavailable_id,
            None,
            "session_unavailable",
            "RESEARCH_SNAPSHOT_SESSION_UNAVAILABLE",
        ),
        (missing_id, session, "missing", "RESEARCH_SNAPSHOT_NOT_FOUND"),
        (
            mismatch_id,
            session,
            "symbol_mismatch",
            "RESEARCH_SNAPSHOT_SYMBOL_MISMATCH",
        ),
    )
    for snapshot_id, candidate_session, expected_status, expected_code in cases:
        payload = market_assistant_service.answer_market_assistant_question(
            symbol="000001",
            question="Summarize the candidate evidence.",
            locale="en",
            start=date(2026, 7, 10),
            end=date(2026, 7, 11),
            provider_name="mock",
            research_snapshot_id=snapshot_id,
            session=candidate_session,
        )

        assert payload["status"] == "degraded"
        assert payload["context"]["research_snapshot"]["status"] == expected_status
        assert payload["context"]["research_snapshot"]["applied"] is False
        assert any(
            diagnostic.get("code") == expected_code
            for diagnostic in payload["diagnostics"]
        )
        assert not any(
            citation["source"] == "research_shortlist"
            for citation in payload["citations"]
        )

    assert lookup_ids == [missing_id, mismatch_id]


def test_market_assistant_localizes_unapplied_snapshot_diagnostic_for_chinese_fallback(
    monkeypatch,
):
    patch_snapshot_test_dependencies(monkeypatch)
    monkeypatch.setattr(
        market_assistant_service,
        "get_platform_settings",
        lambda: {"llm_provider": "mock", "llm_api_key": ""},
    )

    payload = market_assistant_service.answer_market_assistant_question(
        symbol="000001",
        question="请说明证据缺口。",
        locale="zh",
        start=date(2026, 7, 10),
        end=date(2026, 7, 11),
        provider_name="mock",
        research_snapshot_id="not-a-uuid",
        session=object(),
    )

    snapshot_diagnostic = next(
        diagnostic
        for diagnostic in payload["diagnostics"]
        if diagnostic.get("code") == "RESEARCH_SNAPSHOT_INVALID_ID"
    )
    assert snapshot_diagnostic["message"] == "请求的每日候选快照 ID 无效。"
    assert snapshot_diagnostic["message"] in payload["answer_markdown"]
