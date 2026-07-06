from packages.domain.models import Instrument, Market, ResearchSourceNote


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
