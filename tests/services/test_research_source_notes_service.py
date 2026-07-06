from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.services.research_source_notes import (
    ResearchSourceNoteInput,
    ResearchSourceNoteValidationError,
    create_research_source_note,
    list_citable_research_source_note_citations,
    list_research_source_notes,
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


def test_create_research_source_note_normalizes_and_serializes_metadata():
    session = make_session()

    payload = create_research_source_note(
        ResearchSourceNoteInput(
            title="  Buffett Indicator component review  ",
            source_name="World Bank",
            source_type="valuation_component",
            source_url="https://example.com/gdp",
            symbols=[" aapl ", "AAPL", "msft"],
            tags=[" macro ", "valuation"],
            as_of=date(2026, 7, 3),
            retrieved_at=datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc),
            excerpt="Reviewed GDP and market-cap component excerpt.",
            note="Use this to cross-check Buffett Indicator components.",
            review_status="reviewed",
            is_citable=True,
            metadata={"component": "gdp"},
        ),
        session=session,
    )

    assert payload["title"] == "Buffett Indicator component review"
    assert payload["symbols"] == ["AAPL", "MSFT"]
    assert payload["tags"] == ["macro", "valuation"]
    assert payload["is_citable"] is True
    assert str(payload["citation_id"]).startswith("research_source_note:")
    assert payload["metadata"] == {"component": "gdp"}


def test_draft_notes_are_listed_but_not_citable():
    session = make_session()
    create_research_source_note(
        ResearchSourceNoteInput(
            title="Draft source",
            source_name="SEC search",
            source_type="filing_search",
            source_url="https://example.com/search",
            excerpt="Draft excerpt.",
            review_status="draft",
            is_citable=False,
        ),
        session=session,
    )

    notes = list_research_source_notes(session=session)
    citations = list_citable_research_source_note_citations(session=session)

    assert notes["summary"]["total"] == 1
    assert notes["items"][0]["review_status"] == "draft"
    assert notes["items"][0]["citation_id"] is None
    assert citations == []


def test_citable_notes_require_reviewed_excerpt_and_source_identity():
    session = make_session()

    with pytest.raises(ResearchSourceNoteValidationError) as error:
        create_research_source_note(
            ResearchSourceNoteInput(
                title="Too early",
                source_name="Unknown source",
                source_type="macro_note",
                source_url="https://example.com",
                excerpt="Reviewed excerpt.",
                review_status="draft",
                is_citable=True,
            ),
            session=session,
        )

    assert "Citable notes must have review_status=reviewed." in error.value.errors

    with pytest.raises(ResearchSourceNoteValidationError) as missing_excerpt:
        create_research_source_note(
            ResearchSourceNoteInput(
                title="Missing excerpt",
                source_name="Unknown source",
                source_type="macro_note",
                source_url="https://example.com",
                review_status="reviewed",
                is_citable=True,
            ),
            session=session,
        )

    assert "Citable notes require a reviewed excerpt." in missing_excerpt.value.errors


def test_citable_citation_payload_filters_by_symbol():
    session = make_session()
    first = create_research_source_note(
        ResearchSourceNoteInput(
            title="AAPL valuation note",
            source_name="Manual review",
            source_type="valuation_component",
            source_url="https://example.com/aapl",
            symbols=["AAPL"],
            tags=["valuation"],
            excerpt="AAPL source excerpt.",
            review_status="reviewed",
            is_citable=True,
        ),
        session=session,
    )
    create_research_source_note(
        ResearchSourceNoteInput(
            title="MSFT valuation note",
            source_name="Manual review",
            source_type="valuation_component",
            source_url="https://example.com/msft",
            symbols=["MSFT"],
            tags=["valuation"],
            excerpt="MSFT source excerpt.",
            review_status="reviewed",
            is_citable=True,
        ),
        session=session,
    )

    citations = list_citable_research_source_note_citations(session=session, symbols=["AAPL"])

    assert len(citations) == 1
    assert citations[0]["id"] == first["citation_id"]
    assert citations[0]["source"] == "research_source_notes"
    assert citations[0]["source_type"] == "research_source_note"
