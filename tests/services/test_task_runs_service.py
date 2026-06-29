from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.services.task_runs import (
    fail_task_run,
    finish_task_run,
    get_latest_task_run_payload,
    get_recent_task_runs_payload,
    start_task_run,
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


def test_task_run_service_records_success_and_latest_payload():
    session = make_session()

    task_run = start_task_run(
        "reports.refresh_daily_watchlist_analysis",
        {"watchlist": "AAPL:US"},
        session=session,
    )
    running = get_latest_task_run_payload(
        session=session,
        task_name="reports.refresh_daily_watchlist_analysis",
    )
    finished = finish_task_run(task_run, {"item_count": 1}, session=session)
    latest = get_latest_task_run_payload(
        session=session,
        task_name="reports.refresh_daily_watchlist_analysis",
    )

    assert running["status"] == "running"
    assert finished["status"] == "succeeded"
    assert latest["task_name"] == "reports.refresh_daily_watchlist_analysis"
    assert latest["status"] == "succeeded"
    assert latest["input_json"] == {"watchlist": "AAPL:US"}
    assert latest["result_json"] == {"item_count": 1}
    assert latest["duration_ms"] >= 0


def test_task_run_service_records_failure_and_recent_payload():
    session = make_session()

    task_run = start_task_run(
        "reports.refresh_daily_watchlist_analysis",
        {"watchlist": "0700:HK"},
        session=session,
    )
    failed = fail_task_run(task_run, "provider timeout", session=session)
    recent = get_recent_task_runs_payload(session=session, limit=1)

    assert failed["status"] == "failed"
    assert failed["error_message"] == "provider timeout"
    assert recent["items"][0]["status"] == "failed"
    assert recent["items"][0]["input_json"] == {"watchlist": "0700:HK"}
