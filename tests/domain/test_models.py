from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import CheckConstraint, UniqueConstraint, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.domain.models import (
    Instrument,
    Market,
    OfficialDisclosure,
    OfficialDisclosureDocument,
    OfficialDisclosureSection,
    ResearchCandidateOutcome,
    ResearchShortlistCandidate,
    ResearchShortlistRun,
    ResearchSourceNote,
)
from packages.shared.database import Base


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
    assert run.generation_task_run_id is None
    assert run.candidates[0].entry_source == "akshare.stock_zh_a_hist"
    assert run.candidates[0].safety_json["research_signal_only"] is True


def test_research_shortlist_run_schema_tracks_generation_task_run_lineage():
    table = ResearchShortlistRun.__table__
    column = table.c.generation_task_run_id
    foreign_key = next(iter(column.foreign_keys))

    assert column.nullable is True
    assert foreign_key.target_fullname == "task_runs.id"
    assert foreign_key.ondelete == "SET NULL"
    assert any(
        index.name == "ix_research_shortlist_runs_generation_task_run_id"
        and [indexed.name for indexed in index.columns]
        == ["generation_task_run_id"]
        for index in table.indexes
    )


def test_research_candidate_outcome_preserves_terminal_result_relationship():
    candidate = ResearchShortlistCandidate(
        symbol="000001",
        name="Example",
        market="CN",
        asset_type="stock",
        rank=1,
        total_score=Decimal("0.8125"),
        minimum_rule_buffer=Decimal("0.6250"),
        entry_trade_date=datetime(2026, 7, 10, tzinfo=timezone.utc).date(),
        entry_close=Decimal("10.500000"),
        entry_provider="akshare",
        entry_source="akshare.stock_zh_a_hist",
        entry_adjustment="qfq",
        entry_source_priority=0,
        entry_ingested_at=datetime(2026, 7, 10, 10, tzinfo=timezone.utc),
    )
    outcome = ResearchCandidateOutcome(
        horizon_sessions=5,
        methodology_version="research_candidate_outcome_v1",
        status="evaluated",
        evaluation_as_of=datetime(2026, 7, 17, tzinfo=timezone.utc).date(),
        available_forward_bars=5,
        maturity_trade_date=datetime(2026, 7, 17, tzinfo=timezone.utc).date(),
        exit_close=Decimal("11.025000"),
        minimum_forward_low=Decimal("10.290000"),
        minimum_forward_low_trade_date=datetime(2026, 7, 13, tzinfo=timezone.utc).date(),
        return_ratio=Decimal("0.0500000000"),
        drawdown_ratio=Decimal("-0.0200000000"),
        benchmark_status="pending",
    )

    candidate.outcomes.append(outcome)

    assert outcome.candidate is candidate
    assert candidate.outcomes == [outcome]
    assert outcome.horizon_sessions == 5
    assert outcome.return_ratio == Decimal("0.0500000000")
    assert outcome.benchmark_status == "pending"


def test_research_candidate_outcome_schema_enforces_terminal_contract():
    table = ResearchCandidateOutcome.__table__
    unique_constraints = {
        constraint.name: {column.name for column in constraint.columns}
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    check_constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert unique_constraints["uq_research_candidate_outcomes_horizon"] == {
        "candidate_id",
        "horizon_sessions",
    }
    assert set(check_constraints) >= {
        "ck_research_candidate_outcomes_horizon_sessions",
        "ck_research_candidate_outcomes_status",
        "ck_research_candidate_outcomes_benchmark_status",
        "ck_research_candidate_outcomes_mature",
        "ck_research_candidate_outcomes_evaluation_order",
        "ck_research_candidate_outcomes_candidate_terminal_values",
        "ck_research_candidate_outcomes_benchmark_terminal_values",
    }
    assert table.c.maturity_trade_date.nullable is False
    assert table.c.return_ratio.type.precision == 20
    assert table.c.return_ratio.type.scale == 10
    assert table.c.drawdown_ratio.type.precision == 20
    assert table.c.drawdown_ratio.type.scale == 10
    assert table.c.benchmark_return_ratio.nullable is True
    assert table.c.excess_return_ratio.nullable is True


def test_research_candidate_outcome_database_enforces_identity_and_cascade():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    market = Market(
        code="CN",
        name="China",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    instrument = Instrument(
        symbol="000001",
        name="Example",
        asset_type="stock",
        currency="CNY",
        market=market,
    )
    run = ResearchShortlistRun(
        generation_key="b" * 64,
        status="committed",
        decision_date=datetime(2026, 7, 10, tzinfo=timezone.utc).date(),
        market="CN",
        asset_type="stock",
        profile_id="balanced_research",
        rule_set="instock_composite_selection_v1",
        scoring_model="daily_research_score_v1",
        locale="en",
        shortlist_limit=10,
        explanation_markdown="Research only.",
    )
    candidate = ResearchShortlistCandidate(
        instrument=instrument,
        symbol="000001",
        name="Example",
        market="CN",
        asset_type="stock",
        rank=1,
        total_score=Decimal("0.8125"),
        minimum_rule_buffer=Decimal("0.6250"),
        entry_trade_date=datetime(2026, 7, 10, tzinfo=timezone.utc).date(),
        entry_close=Decimal("10.500000"),
        entry_provider="akshare",
        entry_source="akshare.stock_zh_a_hist",
        entry_adjustment="qfq",
        entry_source_priority=0,
        entry_ingested_at=datetime(2026, 7, 10, 10, tzinfo=timezone.utc),
    )
    outcome = ResearchCandidateOutcome(
        horizon_sessions=5,
        status="blocked",
        evaluation_as_of=datetime(2026, 7, 17, tzinfo=timezone.utc).date(),
        available_forward_bars=5,
        maturity_trade_date=datetime(2026, 7, 17, tzinfo=timezone.utc).date(),
        benchmark_status="not_applicable",
        diagnostics_json=[{"code": "ENTRY_BAR_REVISED"}],
    )
    run.candidates.append(candidate)
    candidate.outcomes.append(outcome)

    try:
        session.add(run)
        session.commit()
        outcome_id = outcome.id

        outcome.horizon_sessions = 10
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        outcome.status = "pending"
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        outcome.available_forward_bars = 4
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        outcome.status = "evaluated"
        outcome.benchmark_status = "pending"
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        outcome.evaluation_as_of = datetime(2026, 7, 16, tzinfo=timezone.utc).date()
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        outcome.status = "evaluated"
        outcome.exit_close = Decimal("11.025000")
        outcome.minimum_forward_low = Decimal("10.290000")
        outcome.minimum_forward_low_trade_date = datetime(
            2026, 7, 13, tzinfo=timezone.utc
        ).date()
        outcome.return_ratio = Decimal("0.0500000000")
        outcome.drawdown_ratio = Decimal("-0.0200000000")
        outcome.exit_provider = "akshare"
        outcome.exit_source = "akshare.stock_zh_a_hist"
        outcome.exit_adjustment = "qfq"
        outcome.exit_source_priority = 0
        outcome.exit_ingested_at = datetime(2026, 7, 17, 10, tzinfo=timezone.utc)
        outcome.minimum_low_provider = "akshare"
        outcome.minimum_low_source = "akshare.stock_zh_a_hist"
        outcome.minimum_low_adjustment = "qfq"
        outcome.minimum_low_source_priority = 0
        outcome.minimum_low_ingested_at = datetime(
            2026, 7, 13, 10, tzinfo=timezone.utc
        )
        outcome.benchmark_status = "evaluated"
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        duplicate = ResearchCandidateOutcome(
            candidate=candidate,
            horizon_sessions=5,
            status="blocked",
            evaluation_as_of=datetime(2026, 7, 17, tzinfo=timezone.utc).date(),
            available_forward_bars=5,
            maturity_trade_date=datetime(2026, 7, 17, tzinfo=timezone.utc).date(),
            benchmark_status="not_applicable",
        )
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        candidate_id = candidate.id
        session.expunge_all()
        persisted_candidate = session.get(ResearchShortlistCandidate, candidate_id)
        assert persisted_candidate is not None
        assert "outcomes" not in persisted_candidate.__dict__
        session.delete(persisted_candidate)
        session.commit()
        assert session.get(ResearchCandidateOutcome, outcome_id) is None
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
