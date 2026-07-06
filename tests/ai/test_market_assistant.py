from datetime import date

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
    assert payload["citations"][0]["id"] == "bars_1d:AAPL:2026-01-03"
    assert payload["citations"][0]["source_type"] == "bars"
    assert payload["safety"]["not_investment_advice"] is True
    assert "不构成投资建议" in payload["answer_markdown"]


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
    assert "Use inline citation IDs in square brackets" in prompt
    assert "use only citation IDs listed above" in prompt


def test_market_assistant_generates_research_evidence_citations_for_available_sources(monkeypatch):
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
        lambda symbol, session: {
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
        },
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
        "get_platform_settings",
        lambda: {"llm_provider": "mock", "llm_api_key": "", "llm_api_base": ""},
    )

    payload = market_assistant_service.answer_market_assistant_question(
        symbol="AAPL",
        question="请总结近期研究资料。",
        start=date(2026, 1, 1),
        end=date(2026, 1, 3),
        provider_name="mock",
        session=object(),
    )

    citations_by_source_type = {citation.get("source_type"): citation for citation in payload["citations"]}
    assert "bars" in citations_by_source_type
    assert "technical_indicator" in citations_by_source_type
    assert "fundamental" in citations_by_source_type
    assert "news" in citations_by_source_type
    assert "generated_report" in citations_by_source_type
    assert "research_source_note" in citations_by_source_type
    assert citations_by_source_type["news"]["url"] == "https://example.com/aapl-services"
    assert citations_by_source_type["generated_report"]["id"] == "generated_report:11111111-1111-1111-1111-111111111111"
    assert citations_by_source_type["research_source_note"]["id"].startswith("research_source_note:")
    assert "Reviewed source notebook entries available" in payload["context"]["research_summary"]


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


def test_market_assistant_detects_unknown_llm_citation_ids(monkeypatch):
    class HallucinatingProvider:
        def generate(self, prompt: str) -> str:
            return "### Summary\nUnsupported claim [news:AAPL:unknown]."

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
    monkeypatch.setattr(market_assistant_service, "get_llm_provider", lambda: HallucinatingProvider())

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
    assert any(diagnostic.get("code") == "CITATION_UNKNOWN_ID" for diagnostic in payload["diagnostics"])


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
    monkeypatch.setattr(market_assistant_service, "get_llm_provider", lambda: UnexpectedProvider())

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
    assert payload["citations"] == []
    assert payload["diagnostics"][0]["source"] == "bars_1d"
    assert "没有获取到" in payload["answer_markdown"]


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
    monkeypatch.setattr(market_assistant_service, "get_llm_provider", lambda: FailingProvider())

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
