from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from packages.domain.models import TaskRun
from packages.shared.database import Base
from scripts.task_run_health import WARN_STATUS, check_task_run_health, render_result


FIXED_NOW = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with session_factory() as database_session:
        yield database_session

    Base.metadata.drop_all(engine)


def test_no_task_runs_returns_ok(session: Session) -> None:
    result = check_task_run_health(session, now=FIXED_NOW, stale_minutes=30)

    assert result.status == "OK"
    assert result.message == "no task runs found"
    assert result.recent_count == 0


def test_stale_running_task_returns_warn_without_mutating_status(session: Session) -> None:
    task_run = TaskRun(
        task_name="reports.refresh_daily_stock_analysis",
        status="running",
        started_at=FIXED_NOW - timedelta(minutes=31),
        input_json={},
        created_at=FIXED_NOW - timedelta(minutes=31),
    )
    session.add(task_run)
    session.commit()

    result = check_task_run_health(session, now=FIXED_NOW, stale_minutes=30)
    rendered_result = render_result(result)

    assert result.status == WARN_STATUS
    assert result.stale_running_count == 1
    assert result.stale_task_names == ["reports.refresh_daily_stock_analysis"]
    assert "stale_running=1" in rendered_result
    assert "reports.refresh_daily_stock_analysis" in rendered_result

    session.refresh(task_run)
    assert task_run.status == "running"
    assert task_run.finished_at is None


def test_fresh_heartbeat_keeps_old_running_task_healthy(session: Session) -> None:
    task_run = TaskRun(
        task_name="research.run_daily_research_loop",
        status="running",
        started_at=FIXED_NOW - timedelta(hours=2),
        heartbeat_at=FIXED_NOW - timedelta(minutes=5),
        input_json={},
        created_at=FIXED_NOW - timedelta(hours=2),
    )
    session.add(task_run)
    session.commit()

    result = check_task_run_health(session, now=FIXED_NOW, stale_minutes=30)

    assert result.status == "OK"
    assert result.stale_running_count == 0

    session.refresh(task_run)
    assert task_run.status == "running"


def test_recent_failed_task_returns_warn_with_count_and_task_names(session: Session) -> None:
    failed_task_run = TaskRun(
        task_name="ingestion.ingest_market_data",
        status="failed",
        started_at=FIXED_NOW - timedelta(minutes=15),
        finished_at=FIXED_NOW - timedelta(minutes=14),
        input_json={},
        error_message="provider unavailable",
        created_at=FIXED_NOW - timedelta(minutes=15),
    )
    session.add(failed_task_run)
    session.commit()

    result = check_task_run_health(session, now=FIXED_NOW, stale_minutes=30)
    rendered_result = render_result(result)

    assert result.status == WARN_STATUS
    assert result.failed_last_24h_count == 1
    assert result.failed_task_names == ["ingestion.ingest_market_data"]
    assert "failed_last_24h=1" in rendered_result
    assert "ingestion.ingest_market_data" in rendered_result


def test_database_connection_failure_returns_warn_without_traceback() -> None:
    class BrokenSession:
        def query(self, model: object) -> object:
            raise RuntimeError("database is offline")

    result = check_task_run_health(BrokenSession(), now=FIXED_NOW, stale_minutes=30)  # type: ignore[arg-type]
    rendered_result = render_result(result)

    assert result.status == WARN_STATUS
    assert result.message == "TaskRun database unavailable"
    assert "database is offline" in rendered_result
    assert "Traceback" not in rendered_result
