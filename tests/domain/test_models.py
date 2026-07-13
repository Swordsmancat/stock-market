from datetime import datetime, timezone

from packages.domain.models import (
    Instrument,
    Market,
    OfficialDisclosure,
    OfficialDisclosureDocument,
    OfficialDisclosureSection,
    ResearchShortlistCandidate,
    ResearchShortlistRun,
    ResearchSourceNote,
)


def test_instrument_has_market_identity():
    market = Market(code="US", name="US Stock", timezone="America/New_York", currency="USD")
    instrument = Instrument(symbol="AAPL", name="Apple Inc.", asset_type="stock", currency="USD")
    instrument.market = market
    assert instrument.market.code == "US"
    assert instrument.symbol == "AAPL"


def test_research_source_note_stores_collection_metadata():
    note = ResearchSourceNote(
        title="Buffett Indicator component review",
        source_name="Operator-reviewed source",
        source_type="valuation_component",
        symbols_json=["AAPL"],
        tags_json=["buffett", "macro"],
        excerpt="Reviewed source excerpt.",
        note="Calculation note.",
        ai_follow_up="Summarize valuation gap.",
        review_status="reviewed",
        is_citable=True,
        metadata_json={"component": "market_cap_to_gdp"},
    )

    assert note.title == "Buffett Indicator component review"
    assert note.symbols_json == ["AAPL"]
    assert note.tags_json == ["buffett", "macro"]
    assert note.is_citable is True


def test_official_disclosure_stores_stable_external_identity():
    disclosure = OfficialDisclosure(
        source="cninfo",
        source_document_id="1212345678",
        symbol="000001",
        title="2025 annual report",
        published_at=datetime(2026, 3, 20, tzinfo=timezone.utc),
        source_url="http://www.cninfo.com.cn/new/disclosure/detail?announcementId=1212345678",
        retrieved_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        dedupe_hash="a" * 64,
        metadata_json={"evidence_scope": "metadata_only", "content_ingested": False},
    )

    assert disclosure.source_document_id == "1212345678"
    assert disclosure.metadata_json["content_ingested"] is False


def test_official_disclosure_document_and_section_preserve_content_provenance():
    document = OfficialDisclosureDocument(
        attachment_url="https://static.cninfo.com.cn/finalpage/2026-03-21/1212345678.PDF",
        media_type="application/pdf",
        byte_size=1024,
        sha256="a" * 64,
        storage_path="disclosure-id/hash.pdf",
        retrieved_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        extraction_status="extracted",
        extraction_method="pypdf",
        metadata_json={"content_addressed": True},
    )
    section = OfficialDisclosureSection(
        section_index=0,
        page_number=12,
        heading="Risk Factors",
        topic="risks",
        content_text="Customer concentration is a material risk.",
        content_hash="b" * 64,
    )

    assert document.sha256 == "a" * 64
    assert document.metadata_json["content_addressed"] is True
    assert section.page_number == 12
    assert section.topic == "risks"


def test_research_shortlist_models_preserve_frozen_decision_evidence():
    run = ResearchShortlistRun(
        generation_key="a" * 64,
        status="committed",
        decision_date=datetime(2026, 7, 10, tzinfo=timezone.utc).date(),
        market="CN",
        asset_type="stock",
        profile_id="quality_value",
        rule_set="instock_composite_selection_v1",
        scoring_model="daily_research_score_v1",
        locale="zh",
        shortlist_limit=10,
        explanation_markdown="Research only.",
    )
    candidate = ResearchShortlistCandidate(
        symbol="000001",
        name="Example",
        market="CN",
        asset_type="stock",
        rank=1,
        total_score=0.8125,
        minimum_rule_buffer=0.625,
        entry_trade_date=datetime(2026, 7, 10, tzinfo=timezone.utc).date(),
        entry_close=10.5,
        entry_provider="akshare",
        entry_source="akshare.stock_zh_a_hist",
        entry_adjustment="qfq",
        entry_source_priority=0,
        entry_ingested_at=datetime(2026, 7, 10, 10, tzinfo=timezone.utc),
        safety_json={"research_signal_only": True},
    )
    run.candidates.append(candidate)

    assert run.scoring_model == "daily_research_score_v1"
    assert run.candidates[0].entry_source == "akshare.stock_zh_a_hist"
    assert run.candidates[0].safety_json["research_signal_only"] is True
