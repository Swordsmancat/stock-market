from datetime import datetime, timezone

from packages.domain.models import Instrument, Market, OfficialDisclosure, ResearchSourceNote


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
