from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import (
    DailyBar,
    Exchange,
    FundamentalSnapshot,
    Instrument,
    Market,
    ResearchCandidateOutcome,
    ResearchEvidenceBackfill,
    ResearchShortlistCandidate,
    ResearchShortlistRun,
    TaskRun,
    TechnicalIndicator,
)
from packages.services.daily_research_loop import (
    DAILY_RESEARCH_LOOP_TASK_NAME,
    DailyResearchLoopInput,
    run_daily_research_loop,
)
from packages.shared.database import Base


UTC = timezone.utc
HISTORY_START = date(2026, 6, 9)
PRIOR_DECISION_DATE = date(2026, 7, 1)
VERIFIED_DECISION_DATE = date(2026, 7, 13)
NOW = datetime(2026, 7, 13, 13, 30, tzinfo=UTC)


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    database_session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )()
    try:
        yield database_session
    finally:
        database_session.close()
        Base.metadata.drop_all(engine)


def test_ready_daily_research_loop_matures_once_then_reuses(session: Session) -> None:
    first_task_run, second_task_run = _seed_ready_loop_state(session)
    payload = DailyResearchLoopInput(
        profile_id="quality_value",
        shortlist_limit=3,
        use_llm=False,
    )

    first = run_daily_research_loop(
        payload,
        session=session,
        task_run_id=first_task_run.id,
        now=NOW,
    )

    assert first["status"] == "completed"
    assert first["watermark"]["verified_completed_through"] == "2026-07-13"
    assert first["watermark"]["coverage"]["coverage_ratio"] == 1.0
    assert first["outcomes"]["processed_run_count"] == 1
    assert first["outcomes"]["final_evaluated_horizon_count"] == 1
    assert first["publication"]["status"] == "created"
    assert first["publication"]["generation_task_run_id"] == str(first_task_run.id)
    assert first["publication"]["item_count"] == 3

    published_run_id = first["publication"]["shortlist_run_id"]
    outcome = session.query(ResearchCandidateOutcome).one()
    assert outcome.horizon_sessions == 5
    assert outcome.status == "evaluated"
    assert outcome.evaluation_task_run_id == first_task_run.id
    outcome_snapshot = (
        outcome.id,
        outcome.maturity_trade_date,
        outcome.return_ratio,
        outcome.evaluation_task_run_id,
    )

    second = run_daily_research_loop(
        payload,
        session=session,
        task_run_id=second_task_run.id,
        now=NOW,
    )

    assert second["status"] == "completed"
    assert second["outcomes"]["processed_run_count"] == 0
    assert second["publication"]["status"] == "reused"
    assert second["publication"]["shortlist_run_id"] == published_run_id
    assert second["publication"]["generation_task_run_id"] == str(first_task_run.id)
    session.expire_all()
    persisted_outcome = session.query(ResearchCandidateOutcome).one()
    assert (
        persisted_outcome.id,
        persisted_outcome.maturity_trade_date,
        persisted_outcome.return_ratio,
        persisted_outcome.evaluation_task_run_id,
    ) == outcome_snapshot
    assert session.query(ResearchCandidateOutcome).count() == 1
    assert session.query(ResearchShortlistRun).count() == 2
    assert session.query(ResearchShortlistCandidate).count() == 4
    assert (
        session.query(ResearchShortlistRun)
        .filter(ResearchShortlistRun.generation_task_run_id == second_task_run.id)
        .count()
        == 0
    )
    assert (
        session.query(ResearchCandidateOutcome)
        .filter(ResearchCandidateOutcome.evaluation_task_run_id == second_task_run.id)
        .count()
        == 0
    )


def _seed_ready_loop_state(session: Session) -> tuple[TaskRun, TaskRun]:
    market = Market(
        code="CN",
        name="China A-share",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    session.add(market)
    session.flush()

    instruments: list[Instrument] = []
    for index, (exchange_code, symbol) in enumerate(
        (("SSE", "600000"), ("SZSE", "000001"), ("BSE", "830000"))
    ):
        exchange = Exchange(
            market_id=market.id,
            code=exchange_code,
            name=exchange_code,
        )
        instrument = Instrument(
            symbol=symbol,
            name=f"Research {symbol}",
            market_id=market.id,
            exchange=exchange,
            asset_type="stock",
            currency="CNY",
            is_active=True,
            universe_provider="akshare",
        )
        session.add_all([exchange, instrument])
        session.flush()
        instruments.append(instrument)

        close = Decimal(10 + index)
        for offset in range((VERIFIED_DECISION_DATE - HISTORY_START).days + 1):
            trade_date = HISTORY_START + timedelta(days=offset)
            session.add(
                DailyBar(
                    instrument_id=instrument.id,
                    trade_date=trade_date,
                    open=close,
                    high=close + Decimal("1"),
                    low=close - Decimal("1"),
                    close=close,
                    volume=Decimal("1000000"),
                    amount=Decimal("10000000"),
                    provider="akshare",
                    source="akshare.stock_zh_a_hist",
                    adjustment="qfq",
                    source_priority=0,
                    ingested_at=datetime.combine(trade_date, time(8), tzinfo=UTC),
                )
            )
        for indicator_code in ("ma", "rsi", "mfi"):
            session.add(
                TechnicalIndicator(
                    instrument_id=instrument.id,
                    timeframe="1d",
                    as_of=datetime.combine(
                        VERIFIED_DECISION_DATE,
                        time(8),
                        tzinfo=UTC,
                    ),
                    indicator_code=indicator_code,
                    params={},
                    value_json={"value": 50},
                )
            )
        session.add(
            FundamentalSnapshot(
                symbol=symbol,
                as_of=date(2026, 6, 30),
                currency="CNY",
                pe_ratio=Decimal("12"),
                revenue_growth=Decimal("0.20"),
                net_margin=Decimal("0.18"),
                debt_to_assets=Decimal("0.30"),
                source="akshare",
            )
        )

    first_task_run = _task_run(NOW - timedelta(minutes=2))
    second_task_run = _task_run(NOW - timedelta(minutes=1))
    session.add_all([first_task_run, second_task_run])
    session.add(
        ResearchEvidenceBackfill(
            market="CN",
            provider="akshare",
            run_kind="baseline",
            status="succeeded",
            evidence_kinds_json=["daily_bars", "technical_indicators", "fundamentals"],
            scope_symbols_json=[instrument.symbol for instrument in instruments],
            start_date=HISTORY_START,
            end_date=VERIFIED_DECISION_DATE,
            phase="completed",
            finished_at=NOW - timedelta(hours=1),
            created_at=NOW - timedelta(hours=2),
            updated_at=NOW - timedelta(hours=1),
        )
    )

    prior_run = ResearchShortlistRun(
        generation_key="0" * 64,
        status="committed",
        decision_date=PRIOR_DECISION_DATE,
        generated_at=datetime.combine(PRIOR_DECISION_DATE, time(9), tzinfo=UTC),
        market="CN",
        asset_type="stock",
        profile_id="quality_value",
        rule_set="instock_composite_selection_v1",
        scoring_model="daily_research_score_v1",
        locale="zh",
        shortlist_limit=1,
        default_criteria_json={},
        effective_criteria_json={},
        overrides_json={},
        dimension_weights_json={},
        candidate_scope_json={},
        coverage_json={},
        diagnostics_json=[],
        explanation_markdown="Frozen prior research cohort.",
        model_json={},
        citations_json=[],
        safety_json={},
        research_signal_only=True,
    )
    prior_candidate = ResearchShortlistCandidate(
        run=prior_run,
        instrument_id=instruments[0].id,
        symbol=instruments[0].symbol,
        name=instruments[0].name,
        market="CN",
        asset_type="stock",
        rank=1,
        total_score=Decimal("0.8000"),
        minimum_rule_buffer=Decimal("0.1000"),
        entry_trade_date=PRIOR_DECISION_DATE,
        entry_close=Decimal("10"),
        entry_provider="akshare",
        entry_source="akshare.stock_zh_a_hist",
        entry_adjustment="qfq",
        entry_source_priority=0,
        entry_ingested_at=datetime.combine(
            PRIOR_DECISION_DATE,
            time(8),
            tzinfo=UTC,
        ),
        factor_scores_json=[],
        supporting_factors_json=[],
        opposing_factors_json=[],
        data_gaps_json=[],
        invalidation_conditions_json=[],
        evidence_json={},
        matched_rules_json=[],
        citations_json=[],
        safety_json={},
    )
    session.add_all([prior_run, prior_candidate])
    session.commit()
    return first_task_run, second_task_run


def _task_run(started_at: datetime) -> TaskRun:
    return TaskRun(
        task_name=DAILY_RESEARCH_LOOP_TASK_NAME,
        status="running",
        started_at=started_at,
        heartbeat_at=started_at,
        input_json={},
        created_at=started_at,
    )
