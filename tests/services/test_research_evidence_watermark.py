from datetime import date, datetime, time, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import (
    DailyBar,
    Exchange,
    Instrument,
    Market,
    ResearchEvidenceBackfill,
    TaskRun,
)
from packages.services.research_evidence_backfill import (
    get_active_research_evidence_backfill,
    resolve_completed_daily_bar_watermark,
)
from packages.shared.database import Base


UTC = timezone.utc
POST_CLOSE = datetime(2026, 7, 13, 10, tzinfo=UTC)


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    database_session = sessionmaker(bind=engine)()
    try:
        yield database_session
    finally:
        database_session.close()
        Base.metadata.drop_all(engine)


def seed_universe(session: Session, *, symbols_per_exchange: int) -> list[Instrument]:
    market = Market(
        code="CN",
        name="China A Share",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    session.add(market)
    session.flush()
    instruments: list[Instrument] = []
    for exchange_code, prefix in (("SSE", "600"), ("SZSE", "000"), ("BSE", "830")):
        exchange = Exchange(
            market_id=market.id,
            code=exchange_code,
            name=exchange_code,
        )
        session.add(exchange)
        session.flush()
        for index in range(symbols_per_exchange):
            instrument = Instrument(
                symbol=f"{prefix}{index:03d}",
                name=f"{exchange_code} {index}",
                market_id=market.id,
                exchange_id=exchange.id,
                asset_type="stock",
                currency="CNY",
                is_active=True,
                universe_provider="akshare",
            )
            session.add(instrument)
            instruments.append(instrument)
    session.commit()
    return instruments


def add_backfill(
    session: Session,
    *,
    start_date: date,
    end_date: date,
    run_kind: str = "baseline",
    status: str = "succeeded",
    evidence_kinds: list[str] | None = None,
    task_run: TaskRun | None = None,
    created_at: datetime | None = None,
) -> ResearchEvidenceBackfill:
    finished_at = created_at or datetime(2026, 7, 13, 9, tzinfo=UTC)
    run = ResearchEvidenceBackfill(
        task_run_id=task_run.id if task_run is not None else None,
        market="CN",
        provider="akshare",
        run_kind=run_kind,
        status=status,
        evidence_kinds_json=evidence_kinds or ["daily_bars"],
        scope_symbols_json=[],
        start_date=start_date,
        end_date=end_date,
        phase="completed",
        finished_at=finished_at if status in {"succeeded", "partial"} else None,
        created_at=finished_at,
        updated_at=finished_at,
    )
    session.add(run)
    session.commit()
    return run


def add_bars(
    session: Session,
    instruments: list[Instrument],
    trade_date: date,
    *,
    ingested_at: datetime | None = None,
) -> None:
    completed_at = ingested_at or datetime.combine(trade_date, time(8), tzinfo=UTC)
    for instrument in instruments:
        session.add(
            DailyBar(
                instrument_id=instrument.id,
                trade_date=trade_date,
                open=Decimal("10"),
                high=Decimal("11"),
                low=Decimal("9"),
                close=Decimal("10"),
                volume=Decimal("100"),
                provider="akshare",
                source="akshare.stock_zh_a_hist",
                adjustment="qfq",
                source_priority=0,
                ingested_at=completed_at,
            )
        )
    session.commit()


def test_active_backfill_defers_before_reading_terminal_provenance(session: Session):
    seed_universe(session, symbols_per_exchange=1)
    active = add_backfill(
        session,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 13),
        status="running",
    )

    found = get_active_research_evidence_backfill(
        session=session,
        market=" cn ",
        provider="AKSHARE",
    )
    payload = resolve_completed_daily_bar_watermark(session=session, now=POST_CLOSE)

    assert found.id == active.id
    assert payload["status"] == "not_ready"
    assert payload["code"] == "ACTIVE_EVIDENCE_BACKFILL"
    assert payload["active_backfill"]["id"] == str(active.id)
    assert payload["verified_completed_through"] is None


def test_only_finished_full_scope_daily_bar_runs_are_eligible(session: Session):
    seed_universe(session, symbols_per_exchange=1)
    for run_kind, status, evidence_kinds in (
        ("canary", "succeeded", ["daily_bars"]),
        ("fundamental_shard", "succeeded", ["fundamentals"]),
        ("retry_failed", "succeeded", ["daily_bars"]),
        ("baseline", "failed", ["daily_bars"]),
        ("incremental", "succeeded", ["fundamentals"]),
    ):
        add_backfill(
            session,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 12),
            run_kind=run_kind,
            status=status,
            evidence_kinds=evidence_kinds,
        )

    payload = resolve_completed_daily_bar_watermark(session=session, now=POST_CLOSE)

    assert payload["status"] == "no_data"
    assert payload["code"] == "NO_ELIGIBLE_DAILY_BAR_BACKFILL"


def test_watermark_falls_back_from_partial_date_then_accepts_exactly_95_percent(
    session: Session,
):
    instruments = seed_universe(session, symbols_per_exchange=20)
    task_run = TaskRun(
        task_name="ingestion.backfill_a_share_research_evidence",
        status="succeeded",
        started_at=datetime(2026, 7, 13, 8, tzinfo=UTC),
        finished_at=datetime(2026, 7, 13, 9, tzinfo=UTC),
        input_json={},
        result_json={},
    )
    session.add(task_run)
    session.commit()
    backfill = add_backfill(
        session,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 12),
        status="partial",
        task_run=task_run,
    )
    older_date = date(2026, 7, 11)
    newer_date = date(2026, 7, 12)
    add_bars(session, instruments, older_date)
    add_bars(session, instruments[:56], newer_date)

    below_threshold = resolve_completed_daily_bar_watermark(
        session=session,
        now=POST_CLOSE,
    )

    assert below_threshold["status"] == "ready"
    assert below_threshold["verified_completed_through"] == older_date.isoformat()
    assert below_threshold["skipped_newer_date_count"] == 1
    assert below_threshold["backfill_run_id"] == str(backfill.id)
    assert below_threshold["backfill_task_run_id"] == str(task_run.id)
    assert below_threshold["diagnostics"] == ["NEWER_DAILY_BAR_DATE_NOT_READY"]

    add_bars(session, instruments[56:57], newer_date)
    exact_threshold = resolve_completed_daily_bar_watermark(
        session=session,
        now=POST_CLOSE,
    )

    assert exact_threshold["verified_completed_through"] == newer_date.isoformat()
    assert exact_threshold["coverage"]["ready_count"] == 57
    assert exact_threshold["coverage"]["total_count"] == 60
    assert exact_threshold["coverage"]["coverage_ratio"] == pytest.approx(0.95)
    assert exact_threshold["coverage"]["passes_threshold"] is True
    assert exact_threshold["coverage"]["passes_exchange_representation"] is True
    assert all(
        exact_threshold["coverage"]["by_exchange"][exchange]["ready_count"] > 0
        for exchange in ("SSE", "SZSE", "BSE")
    )


def test_current_date_requires_shanghai_close_and_completed_ingestion(session: Session):
    instruments = seed_universe(session, symbols_per_exchange=1)
    current_date = date(2026, 7, 13)
    add_backfill(
        session,
        start_date=date(2026, 7, 12),
        end_date=current_date,
    )
    add_bars(session, instruments, date(2026, 7, 12))
    add_bars(
        session,
        instruments,
        current_date,
        ingested_at=datetime(2026, 7, 13, 8, tzinfo=UTC),
    )

    before_close = resolve_completed_daily_bar_watermark(
        session=session,
        now=datetime(2026, 7, 13, 7, 59, 59, tzinfo=UTC),
    )
    at_close = resolve_completed_daily_bar_watermark(
        session=session,
        now=datetime(2026, 7, 13, 8, tzinfo=UTC),
    )

    assert before_close["verified_completed_through"] == "2026-07-12"
    assert before_close["candidate_date_ceiling"] == "2026-07-12"
    assert at_close["verified_completed_through"] == "2026-07-13"


def test_scan_window_does_not_grow_with_historical_backfill_ranges(session: Session):
    instruments = seed_universe(session, symbols_per_exchange=1)
    add_backfill(
        session,
        start_date=date(2025, 1, 1),
        end_date=date(2026, 7, 12),
    )
    add_bars(session, instruments, date(2026, 6, 11))

    payload = resolve_completed_daily_bar_watermark(session=session, now=POST_CLOSE)

    assert payload["status"] == "no_data"
    assert payload["code"] == "NO_DAILY_BAR_CANDIDATES"
    assert payload["scan_window_days"] == 31
    assert payload["scan_start_date"] == "2026-06-12"
    assert payload["scan_end_date"] == "2026-07-12"


def test_exchange_representation_is_required_independently_of_95_percent(
    session: Session,
):
    instruments = seed_universe(session, symbols_per_exchange=20)
    for instrument in instruments[41:]:
        instrument.is_active = False
    session.commit()
    trade_date = date(2026, 7, 12)
    add_backfill(
        session,
        start_date=date(2026, 7, 1),
        end_date=trade_date,
    )
    add_bars(session, instruments[:40], trade_date)

    payload = resolve_completed_daily_bar_watermark(session=session, now=POST_CLOSE)

    assert payload["status"] == "not_ready"
    assert payload["code"] == "DAILY_BAR_WATERMARK_NOT_READY"
    assert payload["coverage"]["coverage_ratio"] > 0.95
    assert payload["coverage"]["passes_threshold"] is True
    assert payload["coverage"]["passes_exchange_representation"] is False
    assert "MISSING_REQUIRED_EXCHANGE_REPRESENTATION" in payload["diagnostics"]


def test_ready_watermark_uses_newest_eligible_containing_provenance(session: Session):
    instruments = seed_universe(session, symbols_per_exchange=1)
    trade_date = date(2026, 7, 12)
    add_backfill(
        session,
        start_date=date(2026, 7, 1),
        end_date=trade_date,
        created_at=datetime(2026, 7, 13, 8, tzinfo=UTC),
    )
    newest = add_backfill(
        session,
        start_date=date(2026, 7, 10),
        end_date=trade_date,
        run_kind="incremental",
        created_at=datetime(2026, 7, 13, 9, tzinfo=UTC),
    )
    add_bars(session, instruments, trade_date)

    payload = resolve_completed_daily_bar_watermark(session=session, now=POST_CLOSE)

    assert payload["status"] == "ready"
    assert payload["backfill_run_id"] == str(newest.id)
    assert payload["backfill"]["run_kind"] == "incremental"


def test_watermark_query_count_is_constant_for_large_universe(session: Session):
    instruments = seed_universe(session, symbols_per_exchange=50)
    trade_date = date(2026, 7, 12)
    add_backfill(
        session,
        start_date=date(2026, 7, 1),
        end_date=trade_date,
    )
    add_bars(session, instruments, trade_date)
    select_count = 0

    def count_selects(_conn, _cursor, statement, _parameters, _context, _executemany):
        nonlocal select_count
        if statement.lstrip().upper().startswith("SELECT"):
            select_count += 1

    event.listen(session.get_bind(), "before_cursor_execute", count_selects)
    try:
        payload = resolve_completed_daily_bar_watermark(
            session=session,
            now=POST_CLOSE,
        )
    finally:
        event.remove(session.get_bind(), "before_cursor_execute", count_selects)

    assert payload["status"] == "ready"
    assert payload["coverage"]["total_count"] == 150
    assert select_count <= 4
