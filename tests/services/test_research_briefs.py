from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.services import research_briefs
from packages.services.research_briefs import (
    ResearchBriefGenerateInput,
    generate_and_store_research_brief,
    list_research_briefs,
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


def market_overview_fixture() -> dict[str, object]:
    return {
        "generated_at": "2026-07-07T01:02:03+00:00",
        "provider": "mock",
        "dashboard_brief": {
            "status": "ok",
            "generated_at": "2026-07-07T01:02:03+00:00",
            "sections": [
                {
                    "id": "what_changed",
                    "title": "What changed",
                    "items": ["Buffett Indicator source review is ready."],
                }
            ],
            "citations": [
                {
                    "id": "market_indicator:buffett_indicator_us:2026-07-01",
                    "label": "Buffett Indicator",
                    "source": "market_indicators",
                    "source_type": "macro_indicator",
                    "as_of": "2026-07-01",
                },
                {
                    "id": "research_source_note:note-1",
                    "label": "Market cap source note",
                    "source": "research_source_notes",
                    "source_type": "research_source_note",
                    "as_of": "2026-07-01",
                },
            ],
            "diagnostics": [],
        },
        "information_sources": {
            "items": [
                {
                    "id": "buffett_manual_valuation_components",
                    "label": "Buffett Indicator manual components",
                    "status": "needs_manual_seed",
                    "next_action": "Prepare market-cap and GDP seed evidence.",
                }
            ]
        },
        "research_follow_up_queue": {
            "summary": {"total": 1, "ai_summary_question": 1},
            "items": [
                {
                    "id": "source_note_ai_follow_up:note-1",
                    "kind": "ai_summary_question",
                    "title": "Check Buffett components",
                    "prompt": "Verify market-cap and GDP period alignment.",
                    "citation_policy": "citable",
                    "citation_id": "research_source_note:note-1",
                }
            ],
            "diagnostics": [],
        },
    }


def test_generate_research_brief_uses_deterministic_fallback_without_llm(monkeypatch):
    session = make_session()
    monkeypatch.setattr(research_briefs, "get_market_overview_payload", lambda **_: market_overview_fixture())
    monkeypatch.setattr(
        research_briefs,
        "get_platform_settings",
        lambda: {"llm_provider": "mock", "llm_api_key": "", "llm_api_base": ""},
    )

    payload = generate_and_store_research_brief(
        ResearchBriefGenerateInput(provider_name="mock", locale="en"),
        session=session,
    )

    assert payload["status"] == "stored"
    assert payload["brief_type"] == "evidence_center"
    assert "### Summary" in payload["content_markdown"]
    assert "[market_indicator:buffett_indicator_us:2026-07-01]" in payload["content_markdown"]
    assert payload["model"]["used_llm"] is False
    assert payload["model"]["name"] == "research-brief-deterministic-fallback"
    assert payload["source_summary"]["source_mix"]["research_source_note_citations"] == 1
    assert payload["safety"]["no_buy_sell_hold"] is True

    listed = list_research_briefs(session=session)
    assert listed["summary"] == {"total": 1, "returned": 1}
    assert listed["items"][0]["id"] == payload["id"]


def test_generate_research_brief_stores_valid_llm_answer(monkeypatch):
    session = make_session()
    monkeypatch.setattr(research_briefs, "get_market_overview_payload", lambda **_: market_overview_fixture())
    monkeypatch.setattr(
        research_briefs,
        "get_platform_settings",
        lambda: {"llm_provider": "openai", "llm_api_key": "test-key", "llm_api_base": "http://llm.test"},
    )

    class FakeProvider:
        def generate(self, prompt: str) -> str:
            assert "Allowed citations" in prompt
            return (
                "### Summary\n"
                "- Buffett context is available [market_indicator:buffett_indicator_us:2026-07-01].\n"
                "### Safety Note\n"
                "- Research only."
            )

    monkeypatch.setattr(research_briefs, "get_llm_provider", lambda: FakeProvider())

    payload = generate_and_store_research_brief(
        ResearchBriefGenerateInput(provider_name="mock", locale="en", title="Weekly macro note"),
        session=session,
    )

    assert payload["title"] == "Weekly macro note"
    assert payload["model"]["used_llm"] is True
    assert payload["model"]["provider"] == "openai"
    assert "Buffett context is available" in payload["content_markdown"]


def test_generate_research_brief_falls_back_on_unknown_llm_citation(monkeypatch):
    session = make_session()
    monkeypatch.setattr(research_briefs, "get_market_overview_payload", lambda **_: market_overview_fixture())
    monkeypatch.setattr(
        research_briefs,
        "get_platform_settings",
        lambda: {"llm_provider": "openai", "llm_api_key": "test-key", "llm_api_base": "http://llm.test"},
    )

    class FakeProvider:
        def generate(self, prompt: str) -> str:
            return "Invented evidence [market_indicator:not-present:2026-07-01]."

    monkeypatch.setattr(research_briefs, "get_llm_provider", lambda: FakeProvider())

    payload = generate_and_store_research_brief(
        ResearchBriefGenerateInput(provider_name="mock", locale="en"),
        session=session,
    )

    assert payload["model"]["used_llm"] is False
    assert payload["model"]["fallback_reason"] == "LLM citation validation failed: unknown citation id."
    assert "market_indicator:not-present" not in payload["content_markdown"]
    assert any(diagnostic.get("code") == "CITATION_UNKNOWN_ID" for diagnostic in payload["diagnostics"])
