from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

import packages.domain.models  # noqa: F401
from packages.services import research_shortlist_outcomes
from packages.domain.models import (
    DailyBar,
    Instrument,
    Market,
    ResearchCandidateOutcome,
    ResearchShortlistCandidate,
    ResearchShortlistRun,
)
from packages.services.research_shortlist_outcomes import (
    evaluate_research_shortlist_outcomes,
    get_research_shortlist_outcome_tracking,
    get_research_shortlist_outcomes,
)
from packages.shared.database import Base


UTC = timezone.utc
SHANGHAI_CLOSE_UTC = time(8, 30)
DECISION_DATE = date(2026, 7, 1)
NOW = datetime(2026, 7, 13, 12, tzinfo=UTC)
FAR_NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def seed_committed_run(
    session,
    *,
    symbol: str = "000001",
    decision_date: date = DECISION_DATE,
    existing_instrument: Instrument | None = None,
):
    market = session.query(Market).filter(Market.code == "CN").one_or_none()
    if market is None:
        market = Market(
            code="CN",
            name="China",
            timezone="Asia/Shanghai",
            currency="CNY",
        )
    if existing_instrument is None:
        instrument = Instrument(
            symbol=symbol,
            name=f"Stock {symbol}",
            market=market,
            asset_type="stock",
            currency="CNY",
            is_active=True,
        )
    else:
        instrument = existing_instrument
        symbol = instrument.symbol
    run = ResearchShortlistRun(
        generation_key=f"generation-{symbol}-{decision_date.isoformat()}",
        status="committed",
        decision_date=decision_date,
        generated_at=datetime.combine(decision_date, time(9), tzinfo=UTC),
        market="CN",
        asset_type="stock",
        profile_id="balanced_research",
        rule_set="instock_composite_selection_v1",
        scoring_model="daily_research_score_v1",
        locale="zh",
        shortlist_limit=10,
        default_criteria_json={},
        effective_criteria_json={},
        overrides_json={},
        dimension_weights_json={},
        candidate_scope_json={},
        coverage_json={},
        diagnostics_json=[],
        explanation_markdown="Frozen explanation",
        model_json={},
        citations_json=[],
        safety_json={},
        research_signal_only=True,
    )
    candidate = ResearchShortlistCandidate(
        run=run,
        instrument=instrument,
        symbol=symbol,
        name=instrument.name,
        market="CN",
        asset_type="stock",
        rank=1,
        total_score=Decimal("0.8000"),
        minimum_rule_buffer=Decimal("0.1000"),
        entry_trade_date=decision_date,
        entry_close=Decimal("10.000000"),
        entry_provider="akshare",
        entry_source="akshare.stock_zh_a_hist",
        entry_adjustment="qfq",
        entry_source_priority=0,
        entry_ingested_at=datetime.combine(decision_date, SHANGHAI_CLOSE_UTC, tzinfo=UTC),
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
    session.add_all([instrument, run, candidate])
    session.flush()
    add_bar(session, instrument, decision_date, close="10", low="9.5")
    session.commit()
    return run, candidate, instrument


def add_bar(
    session,
    instrument: Instrument,
    trade_date: date,
    *,
    close: str,
    low: str,
    adjustment: str = "qfq",
    provider: str = "akshare",
    source: str = "akshare.stock_zh_a_hist",
    ingested_at: datetime | None = None,
):
    close_value = Decimal(close)
    low_value = Decimal(low)
    bar = DailyBar(
        instrument_id=instrument.id,
        trade_date=trade_date,
        open=close_value,
        high=max(close_value, low_value),
        low=low_value,
        close=close_value,
        volume=Decimal("1000"),
        amount=Decimal("10000"),
        provider=provider,
        source=source,
        adjustment=adjustment,
        source_priority=0,
        ingested_at=ingested_at or datetime.combine(trade_date, SHANGHAI_CLOSE_UTC, tzinfo=UTC),
    )
    session.add(bar)
    return bar


def add_forward_bars(session, instrument: Instrument, count: int):
    for offset in range(1, count + 1):
        add_bar(
            session,
            instrument,
            DECISION_DATE + timedelta(days=offset),
            close=str(10 + offset),
            low=str(9 + offset),
        )
    session.commit()


def horizon(payload: dict[str, object], sessions: int) -> dict[str, object]:
    horizons = payload["items"][0]["horizons"]
    return next(item for item in horizons if item["horizon_sessions"] == sessions)


def test_get_ready_horizon_remains_pending_until_explicit_evaluation():
    session = make_session()
    run, _, instrument = seed_committed_run(session)
    add_forward_bars(session, instrument, 5)

    payload = get_research_shortlist_outcomes(
        str(run.id),
        session=session,
        now=NOW,
    )

    five_day = horizon(payload, 5)
    assert payload["status"] == "ok"
    assert payload["research_signal_only"] is True
    assert five_day == {
        "horizon_sessions": 5,
        "status": "pending",
        "available_forward_bars": 5,
        "ready_for_evaluation": True,
        "maturity_date": None,
        "exit_close": None,
        "minimum_forward_low": None,
        "minimum_low_date": None,
        "return_ratio": None,
        "drawdown_ratio": None,
        "benchmark": {
            "code": "cn_csi_300",
            "status": "pending",
            "instrument_id": None,
            "entry_date": None,
            "exit_date": None,
            "entry_close": None,
            "exit_close": None,
            "return_ratio": None,
            "excess_return_ratio": None,
            "diagnostics": ["BENCHMARK_INSTRUMENT_MISSING"],
        },
        "diagnostics": [],
    }
    assert horizon(payload, 20)["available_forward_bars"] == 5
    assert horizon(payload, 20)["ready_for_evaluation"] is False
    assert horizon(payload, 60)["available_forward_bars"] == 5
    assert payload["summaries"][0]["total_count"] == 1
    assert payload["summaries"][0]["pending_count"] == 1


def test_forward_bar_counts_only_after_its_own_completed_day_ingestion():
    session = make_session()
    run, _, instrument = seed_committed_run(session)
    add_forward_bars(session, instrument, 4)
    fifth_date = DECISION_DATE + timedelta(days=5)
    add_bar(
        session,
        instrument,
        fifth_date,
        close="15",
        low="14",
        ingested_at=datetime.combine(fifth_date, time(7, 59), tzinfo=UTC),
    )
    session.commit()

    incomplete = get_research_shortlist_outcomes(
        run.id,
        session=session,
        now=NOW,
    )

    assert horizon(incomplete, 5)["available_forward_bars"] == 4
    assert horizon(incomplete, 5)["ready_for_evaluation"] is False
    assert horizon(incomplete, 5)["diagnostics"] == ["INCOMPLETE_FORWARD_BAR_IGNORED"]

    bar = session.get(DailyBar, (instrument.id, fifth_date))
    bar.ingested_at = datetime.combine(fifth_date, time(8), tzinfo=UTC)
    session.commit()

    completed = get_research_shortlist_outcomes(
        run.id,
        session=session,
        now=NOW,
    )
    assert horizon(completed, 5)["available_forward_bars"] == 5
    assert horizon(completed, 5)["ready_for_evaluation"] is True


def test_later_date_backfill_makes_historical_trade_date_eligible():
    session = make_session()
    run, _, instrument = seed_committed_run(session)
    add_forward_bars(session, instrument, 4)
    fifth_date = DECISION_DATE + timedelta(days=5)
    add_bar(
        session,
        instrument,
        fifth_date,
        close="15",
        low="14",
        ingested_at=datetime(2026, 7, 10, 1, tzinfo=UTC),
    )
    session.commit()

    payload = get_research_shortlist_outcomes(
        run.id,
        session=session,
        as_of=fifth_date,
        now=NOW,
    )

    assert horizon(payload, 5)["available_forward_bars"] == 5
    assert horizon(payload, 5)["ready_for_evaluation"] is True


def test_public_cutoff_lags_one_day_and_trusted_watermark_stays_internal():
    session = make_session()
    run, _, instrument = seed_committed_run(session)
    add_forward_bars(session, instrument, 4)
    add_bar(
        session,
        instrument,
        NOW.astimezone(ZoneInfo("Asia/Shanghai")).date(),
        close="15",
        low="14",
        ingested_at=NOW,
    )
    session.commit()

    public = get_research_shortlist_outcomes(run.id, session=session, now=NOW)
    assert public["as_of"] == "2026-07-12"
    assert horizon(public, 5)["available_forward_bars"] == 4

    verified = get_research_shortlist_outcomes(
        run.id,
        session=session,
        as_of=date(2026, 7, 13),
        verified_completed_through=date(2026, 7, 13),
        now=NOW,
    )
    assert horizon(verified, 5)["available_forward_bars"] == 5

    with pytest.raises(ValueError, match="on or before 2026-07-12"):
        get_research_shortlist_outcomes(
            run.id,
            session=session,
            as_of=date(2026, 7, 13),
            now=NOW,
        )

    with pytest.raises(ValueError, match="not complete before 16:00"):
        get_research_shortlist_outcomes(
            run.id,
            session=session,
            verified_completed_through=date(2026, 7, 13),
            now=datetime(2026, 7, 13, 7, 59, tzinfo=UTC),
        )


def test_evaluate_freezes_candidate_result_and_reuses_it_after_bar_replacement():
    session = make_session()
    run, _, instrument = seed_committed_run(session)
    add_forward_bars(session, instrument, 5)

    first = evaluate_research_shortlist_outcomes(
        run.id,
        session=session,
        now=NOW,
    )

    first_five = horizon(first, 5)
    assert first_five["status"] == "evaluated"
    assert first_five["maturity_date"] == "2026-07-06"
    assert first_five["exit_close"] == 15.0
    assert first_five["minimum_forward_low"] == 10.0
    assert first_five["minimum_low_date"] == "2026-07-02"
    assert first_five["return_ratio"] == pytest.approx(0.5)
    assert first_five["drawdown_ratio"] == 0.0
    assert first_five["benchmark"]["status"] == "pending"
    assert first_five["benchmark"]["return_ratio"] is None
    assert first_five["benchmark"]["diagnostics"] == ["BENCHMARK_INSTRUMENT_MISSING"]
    summary = first["summaries"][0]
    assert summary == {
        "horizon_sessions": 5,
        "total_count": 1,
        "evaluated_count": 1,
        "pending_count": 0,
        "blocked_count": 0,
        "return_sample_size": 1,
        "benchmark_sample_size": 0,
        "positive_return_ratio": 1.0,
        "mean_return_ratio": pytest.approx(0.5),
        "median_return_ratio": pytest.approx(0.5),
        "mean_drawdown_ratio": 0.0,
        "mean_excess_return_ratio": None,
    }
    assert session.query(ResearchCandidateOutcome).count() == 1

    terminal_bar = session.get(
        DailyBar,
        (instrument.id, DECISION_DATE + timedelta(days=5)),
    )
    terminal_bar.close = Decimal("99")
    terminal_bar.high = Decimal("99")
    session.commit()

    repeated = evaluate_research_shortlist_outcomes(
        run.id,
        session=session,
        now=NOW,
    )
    assert horizon(repeated, 5)["exit_close"] == 15.0
    assert horizon(repeated, 5)["return_ratio"] == pytest.approx(0.5)
    assert session.query(ResearchCandidateOutcome).count() == 1


def test_benchmark_enrichment_requires_canonical_identity_and_exact_dates():
    session = make_session()
    run, _, candidate_instrument = seed_committed_run(session)
    add_forward_bars(session, candidate_instrument, 5)
    first = evaluate_research_shortlist_outcomes(run.id, session=session, now=NOW)
    assert horizon(first, 5)["benchmark"]["status"] == "pending"

    market = session.query(Market).filter(Market.code == "CN").one()
    stock_000300 = Instrument(
        symbol="000300",
        name="Not the benchmark",
        market=market,
        asset_type="stock",
        currency="CNY",
        is_active=True,
    )
    benchmark = Instrument(
        symbol="cn_csi_300",
        name="CSI 300",
        market=market,
        asset_type="index",
        currency="CNY",
        is_active=True,
    )
    session.add_all([stock_000300, benchmark])
    session.flush()
    add_bar(session, stock_000300, DECISION_DATE, close="100", low="99")
    add_bar(
        session,
        stock_000300,
        DECISION_DATE + timedelta(days=5),
        close="110",
        low="109",
    )
    add_bar(session, benchmark, DECISION_DATE, close="100", low="99")
    add_bar(
        session,
        benchmark,
        DECISION_DATE + timedelta(days=6),
        close="110",
        low="109",
    )
    session.commit()

    wrong_date = evaluate_research_shortlist_outcomes(
        run.id,
        session=session,
        now=NOW,
    )
    assert horizon(wrong_date, 5)["benchmark"]["status"] == "pending"
    assert horizon(wrong_date, 5)["benchmark"]["instrument_id"] == str(benchmark.id)
    assert horizon(wrong_date, 5)["benchmark"]["diagnostics"] == ["BENCHMARK_EXIT_MISSING"]
    assert all(
        horizon(wrong_date, 5)["benchmark"][field] is None
        for field in (
            "entry_date",
            "exit_date",
            "entry_close",
            "exit_close",
            "return_ratio",
            "excess_return_ratio",
        )
    )

    add_bar(
        session,
        benchmark,
        DECISION_DATE + timedelta(days=5),
        close="110",
        low="109",
    )
    session.commit()
    enriched = evaluate_research_shortlist_outcomes(
        run.id,
        session=session,
        now=NOW,
    )
    benchmark_result = horizon(enriched, 5)["benchmark"]
    assert benchmark_result["status"] == "evaluated"
    assert benchmark_result["entry_date"] == "2026-07-01"
    assert benchmark_result["exit_date"] == "2026-07-06"
    assert benchmark_result["return_ratio"] == pytest.approx(0.1)
    assert benchmark_result["excess_return_ratio"] == pytest.approx(0.4)


def test_revised_entry_bar_freezes_blocked_outcome_with_null_metrics():
    session = make_session()
    run, _, instrument = seed_committed_run(session)
    add_forward_bars(session, instrument, 5)
    entry_bar = session.get(DailyBar, (instrument.id, DECISION_DATE))
    entry_bar.close = Decimal("11")
    entry_bar.high = Decimal("11")
    session.commit()

    payload = evaluate_research_shortlist_outcomes(run.id, session=session, now=NOW)

    result = horizon(payload, 5)
    assert result["status"] == "blocked"
    assert result["diagnostics"] == ["ENTRY_BAR_REVISED"]
    assert result["exit_close"] is None
    assert result["return_ratio"] is None
    assert result["drawdown_ratio"] is None
    assert result["benchmark"]["status"] == "not_applicable"

    entry_bar.close = Decimal("10")
    entry_bar.high = Decimal("10")
    session.commit()
    repeated = evaluate_research_shortlist_outcomes(run.id, session=session, now=NOW)
    assert horizon(repeated, 5)["status"] == "blocked"


def test_source_aware_adjustment_allows_provider_mix_but_blocks_raw_qfq_mix():
    compatible_session = make_session()
    compatible_run, _, compatible_instrument = seed_committed_run(compatible_session)
    add_forward_bars(compatible_session, compatible_instrument, 5)
    alternate = compatible_session.get(
        DailyBar,
        (compatible_instrument.id, DECISION_DATE + timedelta(days=5)),
    )
    alternate.provider = "alternate"
    alternate.source = "alternate.qfq.daily"
    compatible_session.commit()
    compatible = evaluate_research_shortlist_outcomes(
        compatible_run.id,
        session=compatible_session,
        now=NOW,
    )
    assert horizon(compatible, 5)["status"] == "evaluated"

    mixed_session = make_session()
    mixed_run, _, mixed_instrument = seed_committed_run(mixed_session)
    add_forward_bars(mixed_session, mixed_instrument, 5)
    legacy_tushare = mixed_session.get(
        DailyBar,
        (mixed_instrument.id, DECISION_DATE + timedelta(days=5)),
    )
    legacy_tushare.provider = "tushare"
    legacy_tushare.source = "tushare.pro.daily"
    legacy_tushare.adjustment = "qfq"
    mixed_session.commit()
    mixed = evaluate_research_shortlist_outcomes(
        mixed_run.id,
        session=mixed_session,
        now=NOW,
    )
    assert horizon(mixed, 5)["status"] == "blocked"
    assert horizon(mixed, 5)["diagnostics"] == [
        "PROVENANCE_ADJUSTMENT_CORRECTED",
        "FORWARD_ADJUSTMENT_MISMATCH",
    ]


def test_legacy_tushare_qfq_labels_normalize_to_one_raw_series():
    session = make_session()
    run, candidate, instrument = seed_committed_run(session)
    candidate.entry_provider = "tushare"
    candidate.entry_source = "tushare.pro.daily"
    candidate.entry_adjustment = "qfq"
    entry = session.get(DailyBar, (instrument.id, DECISION_DATE))
    entry.provider = "tushare"
    entry.source = "tushare.pro.daily"
    entry.adjustment = "qfq"
    add_forward_bars(session, instrument, 5)
    for bar in (
        session.query(DailyBar)
        .filter(DailyBar.instrument_id == instrument.id)
        .filter(DailyBar.trade_date > DECISION_DATE)
    ):
        bar.provider = "tushare"
        bar.source = "tushare.pro.daily"
        bar.adjustment = "qfq"
    session.commit()

    payload = evaluate_research_shortlist_outcomes(run.id, session=session, now=NOW)

    result = horizon(payload, 5)
    assert result["status"] == "evaluated"
    assert result["diagnostics"] == ["PROVENANCE_ADJUSTMENT_CORRECTED"]


@pytest.mark.parametrize(
    ("case", "expected_code"),
    [
        ("zero_close", "FORWARD_PRICE_INVALID"),
        ("invalid_ohlc", "FORWARD_OHLC_INVALID"),
        ("unknown_adjustment", "FORWARD_ADJUSTMENT_UNKNOWN"),
        ("mixed_adjustment", "FORWARD_ADJUSTMENT_MISMATCH"),
    ],
)
def test_mature_invalid_forward_evidence_is_terminally_blocked(case, expected_code):
    session = make_session()
    run, _, instrument = seed_committed_run(session)
    add_forward_bars(session, instrument, 5)
    terminal = session.get(
        DailyBar,
        (instrument.id, DECISION_DATE + timedelta(days=5)),
    )
    if case == "zero_close":
        terminal.close = Decimal("0")
    elif case == "invalid_ohlc":
        terminal.high = Decimal("14")
    elif case == "unknown_adjustment":
        terminal.adjustment = "provider_default"
    else:
        terminal.adjustment = "raw"
    session.commit()

    payload = evaluate_research_shortlist_outcomes(run.id, session=session, now=NOW)

    result = horizon(payload, 5)
    assert result["status"] == "blocked"
    assert result["diagnostics"][-1] == expected_code
    assert result["return_ratio"] is None


def test_concurrent_evaluation_commits_one_terminal_row(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'outcomes.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    setup = session_factory()
    run, _, instrument = seed_committed_run(setup)
    add_forward_bars(setup, instrument, 5)
    run_id = run.id
    setup.close()

    def evaluate_once():
        session = session_factory()
        try:
            return evaluate_research_shortlist_outcomes(
                run_id,
                session=session,
                now=NOW,
            )
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: evaluate_once(), range(2)))

    assert [horizon(payload, 5)["return_ratio"] for payload in results] == [
        pytest.approx(0.5),
        pytest.approx(0.5),
    ]
    verify = session_factory()
    try:
        assert verify.query(ResearchCandidateOutcome).count() == 1
    finally:
        verify.close()


def test_inactive_candidate_remains_in_cohort_and_aggregate_denominator():
    session = make_session()
    run, _, instrument = seed_committed_run(session)
    instrument.is_active = False
    add_forward_bars(session, instrument, 5)
    session.commit()

    payload = evaluate_research_shortlist_outcomes(run.id, session=session, now=NOW)

    result = horizon(payload, 5)
    assert result["status"] == "evaluated"
    assert "INSTRUMENT_INACTIVE" in result["diagnostics"]
    assert payload["summaries"][0]["total_count"] == 1
    assert payload["summaries"][0]["evaluated_count"] == 1


def test_drawdown_uses_lowest_low_within_horizon():
    session = make_session()
    run, _, instrument = seed_committed_run(session)
    add_forward_bars(session, instrument, 5)
    middle = session.get(
        DailyBar,
        (instrument.id, DECISION_DATE + timedelta(days=3)),
    )
    middle.low = Decimal("8")
    session.commit()

    payload = evaluate_research_shortlist_outcomes(run.id, session=session, now=NOW)

    result = horizon(payload, 5)
    assert result["minimum_forward_low"] == 8.0
    assert result["minimum_low_date"] == "2026-07-04"
    assert result["drawdown_ratio"] == pytest.approx(-0.2)


def test_five_day_insert_conflict_does_not_discard_new_20_and_60_day_rows(
    monkeypatch,
):
    session = make_session()
    run, _, instrument = seed_committed_run(session)
    add_forward_bars(session, instrument, 60)

    first = evaluate_research_shortlist_outcomes(
        run.id,
        session=session,
        as_of=DECISION_DATE + timedelta(days=5),
        now=FAR_NOW,
    )
    assert horizon(first, 5)["status"] == "evaluated"
    assert horizon(first, 20)["status"] == "pending"
    assert session.query(ResearchCandidateOutcome).count() == 1

    original_outcome_query = research_shortlist_outcomes._outcomes_for_candidates
    calls = 0

    def stale_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {}
        return original_outcome_query(*args, **kwargs)

    monkeypatch.setattr(
        research_shortlist_outcomes,
        "_outcomes_for_candidates",
        stale_once,
    )

    completed = evaluate_research_shortlist_outcomes(
        run.id,
        session=session,
        now=FAR_NOW,
    )

    assert [horizon(completed, value)["status"] for value in (5, 20, 60)] == [
        "evaluated",
        "evaluated",
        "evaluated",
    ]
    assert session.query(ResearchCandidateOutcome).count() == 3


def test_invalid_benchmark_basis_blocks_only_benchmark_and_stays_immutable():
    session = make_session()
    run, _, candidate_instrument = seed_committed_run(session)
    add_forward_bars(session, candidate_instrument, 5)
    market = session.query(Market).filter(Market.code == "CN").one()
    benchmark = Instrument(
        symbol="cn_csi_300",
        name="CSI 300",
        market=market,
        asset_type="index",
        currency="CNY",
        is_active=True,
    )
    session.add(benchmark)
    session.flush()
    add_bar(session, benchmark, DECISION_DATE, close="100", low="99")
    add_bar(
        session,
        benchmark,
        DECISION_DATE + timedelta(days=5),
        close="110",
        low="109",
        adjustment="raw",
    )
    session.commit()

    first = evaluate_research_shortlist_outcomes(run.id, session=session, now=NOW)

    result = horizon(first, 5)
    assert result["status"] == "evaluated"
    assert result["return_ratio"] == pytest.approx(0.5)
    assert result["benchmark"]["status"] == "blocked"
    assert result["benchmark"]["return_ratio"] is None
    assert result["benchmark"]["diagnostics"] == ["BENCHMARK_ADJUSTMENT_MISMATCH"]

    exit_bar = session.get(
        DailyBar,
        (benchmark.id, DECISION_DATE + timedelta(days=5)),
    )
    exit_bar.adjustment = "qfq"
    session.commit()
    repeated = evaluate_research_shortlist_outcomes(run.id, session=session, now=NOW)
    assert horizon(repeated, 5)["benchmark"]["status"] == "blocked"


def test_historical_read_hides_terminal_observation_after_cutoff():
    session = make_session()
    run, _, instrument = seed_committed_run(session)
    add_forward_bars(session, instrument, 5)
    evaluated = evaluate_research_shortlist_outcomes(run.id, session=session, now=NOW)
    assert horizon(evaluated, 5)["status"] == "evaluated"

    historical = get_research_shortlist_outcomes(
        run.id,
        session=session,
        as_of=DECISION_DATE + timedelta(days=3),
        now=NOW,
    )

    result = horizon(historical, 5)
    assert result["status"] == "pending"
    assert result["available_forward_bars"] == 3
    assert result["maturity_date"] is None
    assert result["return_ratio"] is None


@pytest.mark.parametrize(
    ("forward_count", "horizon_sessions", "ready"),
    [(4, 5, False), (5, 5, True), (19, 20, False), (20, 20, True), (59, 60, False), (60, 60, True)],
)
def test_strict_horizon_boundaries(forward_count, horizon_sessions, ready):
    session = make_session()
    run, _, instrument = seed_committed_run(session)
    add_forward_bars(session, instrument, forward_count)

    payload = get_research_shortlist_outcomes(run.id, session=session, now=FAR_NOW)

    result = horizon(payload, horizon_sessions)
    assert result["available_forward_bars"] == min(forward_count, horizon_sessions)
    assert result["ready_for_evaluation"] is ready


def test_evaluation_ignores_bar_after_horizon():
    session = make_session()
    run, _, instrument = seed_committed_run(session)
    add_forward_bars(session, instrument, 5)
    add_bar(
        session,
        instrument,
        DECISION_DATE + timedelta(days=6),
        close="100",
        low="1",
    )
    session.commit()

    payload = evaluate_research_shortlist_outcomes(run.id, session=session, now=NOW)

    result = horizon(payload, 5)
    assert result["exit_close"] == 15.0
    assert result["minimum_forward_low"] == 10.0
    assert result["drawdown_ratio"] == 0.0


def test_suspension_gaps_count_only_distinct_candidate_bars():
    session = make_session()
    run, _, instrument = seed_committed_run(session)
    for index, offset in enumerate((1, 2, 7, 14, 30), start=1):
        add_bar(
            session,
            instrument,
            DECISION_DATE + timedelta(days=offset),
            close=str(10 + index),
            low=str(9 + index),
        )
    session.commit()

    payload = evaluate_research_shortlist_outcomes(
        run.id,
        session=session,
        now=FAR_NOW,
    )

    result = horizon(payload, 5)
    assert result["status"] == "evaluated"
    assert result["available_forward_bars"] == 5
    assert result["maturity_date"] == "2026-07-31"


def test_tracking_keeps_latest_separate_from_paginated_history():
    session = make_session()
    older, _, _ = seed_committed_run(
        session,
        symbol="000001",
        decision_date=date(2026, 7, 1),
    )
    latest, _, _ = seed_committed_run(
        session,
        symbol="000002",
        decision_date=date(2026, 7, 2),
    )

    payload = get_research_shortlist_outcome_tracking(
        session=session,
        limit=1,
        offset=0,
        now=NOW,
    )

    assert payload["status"] == "ok"
    assert payload["latest"]["run"]["id"] == str(latest.id)
    assert payload["history"][0]["run"]["id"] == str(older.id)
    assert payload["history"][0]["run"]["id"] != payload["latest"]["run"]["id"]
    assert payload["history"][0]["summaries"][0]["total_count"] == 1
    assert payload["limit"] == 1
    assert payload["offset"] == 0
    assert payload["has_more"] is False


def test_tracking_no_data_preserves_safety_and_pagination_shape():
    payload = get_research_shortlist_outcome_tracking(
        session=make_session(),
        limit=10,
        offset=0,
        now=NOW,
    )

    assert payload["status"] == "no_data"
    assert payload["latest"] is None
    assert payload["history"] == []
    assert payload["research_signal_only"] is True
    assert payload["has_more"] is False


def test_tracking_select_count_is_bounded_across_history_limits():
    session = make_session()
    for offset in range(12):
        seed_committed_run(
            session,
            symbol=f"{offset + 1:06d}",
            decision_date=DECISION_DATE + timedelta(days=offset),
        )

    select_counts = []
    for limit in (1, 10, 50):
        statements = []

        def count_selects(_conn, _cursor, statement, _params, _context, _many):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        engine = session.get_bind()
        event.listen(engine, "before_cursor_execute", count_selects)
        try:
            get_research_shortlist_outcome_tracking(
                session=session,
                limit=limit,
                now=NOW,
            )
        finally:
            event.remove(engine, "before_cursor_execute", count_selects)
        select_counts.append(len(statements))

    assert len(set(select_counts)) == 1
    assert select_counts[0] <= 6


def test_candidate_bar_loading_is_keyed_by_candidate_and_bounded_to_sixty_forward_rows():
    session = make_session()
    _, candidate, instrument = seed_committed_run(session)
    for offset in range(1, 401):
        add_bar(
            session,
            instrument,
            DECISION_DATE + timedelta(days=offset),
            close=str(10 + offset),
            low=str(9 + offset),
        )
    session.commit()

    windows = research_shortlist_outcomes._candidate_bars(
        session,
        candidates=[candidate],
        as_of=DECISION_DATE + timedelta(days=400),
    )

    window = windows[candidate.id]
    assert len(window.bars) == 61
    assert window.bars[0].trade_date == DECISION_DATE
    assert window.bars[-1].trade_date == DECISION_DATE + timedelta(days=60)


def test_candidate_bar_loading_keeps_sixty_forward_rows_when_entry_bar_is_missing():
    session = make_session()
    run, candidate, instrument = seed_committed_run(session)
    session.delete(session.get(DailyBar, (instrument.id, DECISION_DATE)))
    for offset in range(1, 62):
        add_bar(
            session,
            instrument,
            DECISION_DATE + timedelta(days=offset),
            close=str(10 + offset),
            low=str(9 + offset),
        )
    session.commit()

    windows = research_shortlist_outcomes._candidate_bars(
        session,
        candidates=[candidate],
        as_of=DECISION_DATE + timedelta(days=61),
    )

    assert len(windows[candidate.id].bars) == 60
    payload = evaluate_research_shortlist_outcomes(
        run.id,
        session=session,
        now=FAR_NOW,
    )
    result = horizon(payload, 60)
    assert result["status"] == "blocked"
    assert result["diagnostics"] == ["ENTRY_BAR_MISSING"]


def test_candidate_bar_windows_are_isolated_for_shared_instrument_entry_dates():
    session = make_session()
    _, first_candidate, instrument = seed_committed_run(session)
    second_entry = DECISION_DATE + timedelta(days=10)
    _, second_candidate, _ = seed_committed_run(
        session,
        decision_date=second_entry,
        existing_instrument=instrument,
    )
    for offset in range(1, 71):
        if offset == 10:
            continue
        add_bar(
            session,
            instrument,
            DECISION_DATE + timedelta(days=offset),
            close=str(10 + offset),
            low=str(9 + offset),
        )
    session.commit()

    windows = research_shortlist_outcomes._candidate_bars(
        session,
        candidates=[first_candidate, second_candidate],
        as_of=DECISION_DATE + timedelta(days=70),
    )

    assert set(windows) == {first_candidate.id, second_candidate.id}
    assert len(windows[first_candidate.id].bars) == 61
    assert len(windows[second_candidate.id].bars) == 61
    assert windows[first_candidate.id].bars[0].trade_date == DECISION_DATE
    assert windows[first_candidate.id].bars[-1].trade_date == DECISION_DATE + timedelta(days=60)
    assert windows[second_candidate.id].bars[0].trade_date == second_entry
    assert windows[second_candidate.id].bars[-1].trade_date == DECISION_DATE + timedelta(days=70)
