from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.worker.tasks import research as research_tasks
from packages.services.daily_research_loop import DailyResearchLoopExecutionError
from packages.services.task_runs import (
    fail_task_run,
    finish_task_run,
    get_latest_task_run_payload,
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


def _result(status: str = "completed") -> dict[str, object]:
    return {
        "status": status,
        "watermark": {
            "status": "ready",
            "verified_completed_through": "2026-07-13",
        },
        "outcomes": {
            "processed_run_count": 0,
            "failed_run_count": 1 if status == "partial_failure" else 0,
        },
        "publication": {"status": "reused"},
        "research_signal_only": True,
    }


def test_daily_research_worker_creates_task_run_and_records_progress(
    monkeypatch,
) -> None:
    session = make_session()
    close = MagicMock(wraps=session.close)
    monkeypatch.setattr(session, "close", close)
    monkeypatch.setattr(research_tasks, "SessionLocal", lambda: session)

    def run_service(_payload, *, progress, **_kwargs):
        progress("outcomes", 1, 3, "Processed one due cohort.")
        return _result()

    monkeypatch.setattr(research_tasks, "run_daily_research_loop", run_service)

    result = research_tasks.run_daily_research_loop_task(
        shortlist_limit=8,
        use_llm=False,
        outcome_run_limit=12,
    )
    latest = get_latest_task_run_payload(
        session,
        "research.run_daily_research_loop",
    )

    assert result["status"] == "completed"
    assert latest["status"] == "succeeded"
    assert latest["input_json"]["shortlist_limit"] == 8
    assert latest["input_json"]["outcome_run_limit"] == 12
    assert latest["result_json"] == result
    assert result["progress"]["phase"] == "outcomes"
    assert result["progress"]["current"] == 1
    assert result["progress"]["total"] == 3
    assert latest["heartbeat_at"] is not None
    close.assert_called_once()


def test_daily_research_worker_reuses_precreated_retry_task_run(monkeypatch) -> None:
    session = make_session()
    monkeypatch.setattr(research_tasks, "SessionLocal", lambda: session)
    existing = start_task_run(
        "research.run_daily_research_loop",
        {"market": "CN", "retry_of": "original-id"},
        session=session,
    )
    monkeypatch.setattr(
        research_tasks,
        "run_daily_research_loop",
        lambda *_args, **_kwargs: _result("deferred"),
    )

    result = research_tasks.run_daily_research_loop_task(
        task_run_id=str(existing.id),
    )
    latest = get_latest_task_run_payload(
        session,
        "research.run_daily_research_loop",
    )

    assert result["status"] == "deferred"
    assert latest["id"] == str(existing.id)
    assert latest["status"] == "succeeded"
    assert latest["input_json"]["retry_of"] == "original-id"


def test_daily_research_worker_preserves_partial_result_then_fails(monkeypatch) -> None:
    session = make_session()
    monkeypatch.setattr(research_tasks, "SessionLocal", lambda: session)
    def partial_service(_payload, *, progress, **_kwargs):
        progress("publication", 2, 3, "Publication completed after one cohort failed.")
        return _result("partial_failure")

    monkeypatch.setattr(research_tasks, "run_daily_research_loop", partial_service)

    with pytest.raises(
        research_tasks.DailyResearchLoopPartialFailure,
        match="1 cohort",
    ):
        research_tasks.run_daily_research_loop_task()

    latest = get_latest_task_run_payload(
        session,
        "research.run_daily_research_loop",
    )
    assert latest["status"] == "failed"
    assert latest["result_json"]["status"] == "partial_failure"
    assert latest["result_json"]["progress"]["phase"] == "publication"
    assert "1 cohort" in latest["error_message"]


def test_daily_research_worker_sanitizes_unexpected_failure_and_closes_session(
    monkeypatch,
) -> None:
    session = make_session()
    close = MagicMock(wraps=session.close)
    monkeypatch.setattr(session, "close", close)
    monkeypatch.setattr(research_tasks, "SessionLocal", lambda: session)

    def fail(*_args, **_kwargs):
        raise RuntimeError("postgresql://user:secret@example.invalid/stock")

    monkeypatch.setattr(research_tasks, "run_daily_research_loop", fail)

    with pytest.raises(RuntimeError, match="secret"):
        research_tasks.run_daily_research_loop_task()

    latest = get_latest_task_run_payload(
        session,
        "research.run_daily_research_loop",
    )
    assert latest["status"] == "failed"
    assert latest["error_message"] == "Daily research loop failed (RuntimeError)."
    assert "secret" not in latest["error_message"]
    close.assert_called_once()


def test_daily_research_worker_persists_unexpected_partial_result(monkeypatch) -> None:
    session = make_session()
    monkeypatch.setattr(research_tasks, "SessionLocal", lambda: session)
    partial_result = {
        "status": "failed",
        "watermark": {"status": "ready", "verified_completed_through": "2026-07-13"},
        "outcomes": {"processed_run_count": 2, "failed_run_count": 0},
        "publication": {
            "status": "failed",
            "code": "SHORTLIST_PUBLICATION_FAILED",
        },
        "research_signal_only": True,
    }

    def fail(_payload, *, progress, **_kwargs):
        progress("publication", 2, 3, "Publishing the verified daily shortlist.")
        raise DailyResearchLoopExecutionError(
            "publication",
            error_type="RuntimeError",
            partial_result=partial_result,
        )

    monkeypatch.setattr(research_tasks, "run_daily_research_loop", fail)

    with pytest.raises(DailyResearchLoopExecutionError):
        research_tasks.run_daily_research_loop_task()

    latest = get_latest_task_run_payload(session, "research.run_daily_research_loop")
    assert latest["status"] == "failed"
    assert latest["result_json"]["watermark"] == partial_result["watermark"]
    assert latest["result_json"]["outcomes"] == partial_result["outcomes"]
    assert latest["result_json"]["progress"]["phase"] == "publication"
    assert latest["result_json"]["progress"]["current"] == 2
    assert latest["error_message"] == (
        "Daily research loop failed during publication (RuntimeError)."
    )


def test_daily_research_worker_replays_succeeded_delivery_without_mutation(
    monkeypatch,
) -> None:
    session = make_session()
    monkeypatch.setattr(research_tasks, "SessionLocal", lambda: session)
    task_run = start_task_run(
        "research.run_daily_research_loop",
        {"market": "CN"},
        session=session,
    )
    expected = _result()
    finish_task_run(task_run, expected, session=session)
    run_service = MagicMock()
    monkeypatch.setattr(research_tasks, "run_daily_research_loop", run_service)

    result = research_tasks.run_daily_research_loop_task(task_run_id=str(task_run.id))
    latest = get_latest_task_run_payload(session, "research.run_daily_research_loop")

    assert result == expected
    assert latest["status"] == "succeeded"
    assert latest["result_json"] == expected
    run_service.assert_not_called()


def test_daily_research_worker_rejects_another_tasks_run_without_mutation(
    monkeypatch,
) -> None:
    session = make_session()
    monkeypatch.setattr(research_tasks, "SessionLocal", lambda: session)
    other = start_task_run(
        "reports.refresh_daily_stock_analysis",
        {"symbol": "AAPL"},
        session=session,
    )
    other_id = other.id

    with pytest.raises(ValueError, match="another task"):
        research_tasks.run_daily_research_loop_task(task_run_id=str(other_id))

    persisted = session.get(packages.domain.models.TaskRun, other_id)
    assert persisted is not None
    assert persisted.status == "running"
    assert persisted.error_message is None


def test_daily_research_worker_rejects_failed_same_task_run_without_mutation(
    monkeypatch,
) -> None:
    session = make_session()
    monkeypatch.setattr(research_tasks, "SessionLocal", lambda: session)
    task_run = start_task_run(
        "research.run_daily_research_loop",
        {"market": "CN"},
        session=session,
    )
    expected_result = _result("partial_failure")
    task_run.result_json = expected_result
    session.commit()
    fail_task_run(task_run, "Original bounded failure.", session=session)
    run_service = MagicMock()
    monkeypatch.setattr(research_tasks, "run_daily_research_loop", run_service)

    with pytest.raises(ValueError, match="not running"):
        research_tasks.run_daily_research_loop_task(task_run_id=str(task_run.id))

    persisted = session.get(packages.domain.models.TaskRun, task_run.id)
    assert persisted is not None
    assert persisted.status == "failed"
    assert persisted.result_json == expected_result
    assert persisted.error_message == "Original bounded failure."
    run_service.assert_not_called()


def test_daily_research_worker_closes_session_when_task_run_start_fails(
    monkeypatch,
) -> None:
    session = MagicMock()
    monkeypatch.setattr(research_tasks, "SessionLocal", lambda: session)
    monkeypatch.setattr(
        research_tasks,
        "start_task_run",
        MagicMock(side_effect=RuntimeError("database unavailable")),
    )

    with pytest.raises(RuntimeError, match="database unavailable"):
        research_tasks.run_daily_research_loop_task()

    session.close.assert_called_once()
