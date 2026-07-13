from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.services.task_runs import (
    expire_stale_task_runs,
    fail_task_run,
    finish_task_run,
    get_latest_task_run_payload,
    get_recent_task_runs_payload,
    retry_task_run_payload,
    start_task_run,
    update_task_run_progress,
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


def test_task_run_service_persists_bounded_progress_payload():
    session = make_session()
    task_run = start_task_run(
        "ingestion.sync_instrument_universe",
        {"market": "CN", "provider": "akshare"},
        session=session,
    )

    payload = update_task_run_progress(
        task_run,
        phase="fetching",
        current=4,
        total=2,
        message="Fetching the provider instrument universe.",
        session=session,
    )

    progress = payload["result_json"]["progress"]
    assert progress["phase"] == "fetching"
    assert progress["current"] == 2
    assert progress["total"] == 2
    assert progress["updated_at"]
    assert payload["heartbeat_at"] == progress["updated_at"]


def test_task_run_heartbeat_prevents_healthy_long_run_from_expiring():
    session = make_session()
    task_run = start_task_run(
        "ingestion.backfill_a_share_research_evidence",
        {"market": "CN", "provider": "akshare"},
        session=session,
    )
    task_run.started_at = task_run.started_at.replace(year=2020)
    session.commit()

    update_task_run_progress(
        task_run,
        phase="daily_bars",
        current=25,
        total=5000,
        message="Processed one bounded batch.",
        session=session,
    )

    expired_count = expire_stale_task_runs(session, timeout_minutes=30)
    latest = get_latest_task_run_payload(
        session,
        "ingestion.backfill_a_share_research_evidence",
    )

    assert expired_count == 0
    assert latest["status"] == "running"
    assert latest["heartbeat_at"] is not None


def test_recent_task_runs_can_filter_by_status():
    session = make_session()
    succeeded_run = start_task_run("reports.refresh_daily_watchlist_analysis", {}, session=session)
    finish_task_run(succeeded_run, {"item_count": 1}, session=session)
    failed_run = start_task_run("reports.refresh_daily_watchlist_analysis", {}, session=session)
    fail_task_run(failed_run, "provider timeout", session=session)

    payload = get_recent_task_runs_payload(session=session, status="failed")

    assert len(payload["items"]) == 1
    assert payload["items"][0]["status"] == "failed"


def test_expire_stale_task_runs_marks_old_running_tasks_failed():
    session = make_session()
    task_run = start_task_run("ingestion.ingest_market_data", {"market": "US"}, session=session)
    task_run.started_at = task_run.started_at.replace(year=2020)
    task_run.heartbeat_at = None
    session.commit()

    expired_count = expire_stale_task_runs(session, timeout_minutes=30)
    latest = get_latest_task_run_payload(session, "ingestion.ingest_market_data")

    assert expired_count == 1
    assert latest["status"] == "failed"
    assert "timed out" in latest["error_message"]


@patch("packages.services.task_dispatch.dispatch_task_run", return_value="celery-task-id-123")
def test_retry_task_run_starts_new_run_with_original_input(mock_dispatch):
    session = make_session()
    failed_run = start_task_run(
        "reports.refresh_daily_watchlist_analysis",
        {"watchlist": "0700:HK"},
        session=session,
    )
    fail_task_run(failed_run, "provider timeout", session=session)
    failed_run.result_json = {"item_count": 1, "quality_diagnostics": {"status": "FAIL"}}
    session.commit()

    payload = retry_task_run_payload(session=session, task_run_id=str(failed_run.id))

    assert payload is not None
    assert payload["status"] == "retry_started"
    assert payload["celery_task_id"] == "celery-task-id-123"
    retry_item = payload["item"]
    assert retry_item["task_name"] == "reports.refresh_daily_watchlist_analysis"
    assert retry_item["status"] == "running"
    assert retry_item["input_json"] == {
        "watchlist": "0700:HK",
        "retry_of": str(failed_run.id),
    }
    assert retry_item["result_json"] is None
    mock_dispatch.assert_called_once()


@patch(
    "packages.services.task_dispatch.dispatch_task_run",
    side_effect=RuntimeError("redis unavailable"),
)
def test_retry_task_run_marks_failed_when_dispatch_fails(mock_dispatch):
    session = make_session()
    failed_run = start_task_run(
        "reports.refresh_daily_watchlist_analysis",
        {"watchlist": "AAPL:US"},
        session=session,
    )
    fail_task_run(failed_run, "provider timeout", session=session)

    payload = retry_task_run_payload(session=session, task_run_id=str(failed_run.id))

    assert payload is not None
    assert payload["status"] == "retry_dispatch_failed"
    assert payload["item"]["status"] == "failed"
    assert "redis unavailable" in payload["item"]["error_message"]
    mock_dispatch.assert_called_once()


@patch("packages.services.task_dispatch.dispatch_task_run", return_value="research-celery-id")
def test_retry_daily_research_loop_preserves_input_and_adds_lineage(mock_dispatch):
    session = make_session()
    failed_run = start_task_run(
        "research.run_daily_research_loop",
        {
            "market": "CN",
            "asset_type": "stock",
            "profile_id": "balanced_research",
            "outcome_run_limit": 25,
            "trigger": "scheduled",
        },
        session=session,
    )
    fail_task_run(failed_run, "Daily research loop failed (RuntimeError).", session=session)

    payload = retry_task_run_payload(session=session, task_run_id=str(failed_run.id))

    assert payload is not None
    assert payload["status"] == "retry_started"
    assert payload["item"]["task_name"] == "research.run_daily_research_loop"
    assert payload["item"]["input_json"] == {
        "market": "CN",
        "asset_type": "stock",
        "profile_id": "balanced_research",
        "outcome_run_limit": 25,
        "trigger": "scheduled",
        "retry_of": str(failed_run.id),
    }
    mock_dispatch.assert_called_once_with(
        "research.run_daily_research_loop",
        payload["item"]["input_json"],
        payload["item"]["id"],
    )
