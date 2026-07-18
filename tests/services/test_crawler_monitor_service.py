from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from packages.domain.models import TaskRun
from packages.services.crawler_monitor import get_crawler_monitor
from packages.shared.database import Base


NOW = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)


def _session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _run(
    *,
    task_name: str,
    status: str,
    input_json: dict,
    age: timedelta,
    heartbeat_age: timedelta | None = None,
    result_json: dict | None = None,
    error_message: str | None = None,
) -> TaskRun:
    started_at = NOW - age
    finished_at = None if status == "running" else started_at + timedelta(minutes=5)
    return TaskRun(
        task_name=task_name,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        input_json=input_json,
        result_json=result_json,
        error_message=error_message,
        heartbeat_at=NOW - heartbeat_age if heartbeat_age is not None else None,
        created_at=started_at,
    )


def test_monitor_separates_shared_tasks_and_classifies_without_mutation():
    session = _session()
    try:
        cn = _run(
            task_name="ingestion.ingest_market_data",
            status="succeeded",
            input_json={"market": "CN", "provider": "akshare"},
            age=timedelta(hours=2),
        )
        us = _run(
            task_name="ingestion.ingest_market_data",
            status="failed",
            input_json={"market": "US", "provider": "https://user:password@example.test"},
            age=timedelta(hours=1),
            error_message="https://user:password@example.test/private",
        )
        incremental = _run(
            task_name="ingestion.backfill_a_share_research_evidence",
            status="running",
            input_json={"run_kind": "incremental"},
            age=timedelta(hours=1),
            heartbeat_age=timedelta(minutes=5),
            result_json={
                "progress": {
                    "phase": "bars",
                    "current": 8,
                    "total": 10,
                    "message": "Processing stored symbols",
                    "updated_at": "2026-07-17T11:55:00+00:00",
                }
            },
        )
        shard = _run(
            task_name="ingestion.backfill_a_share_research_evidence",
            status="running",
            input_json={"run_kind": "fundamental_shard"},
            age=timedelta(hours=2),
            heartbeat_age=timedelta(hours=1),
        )
        session.add_all([cn, us, incremental, shard])
        session.commit()

        payload = get_crawler_monitor(session, now=NOW)
        items = {item["id"]: item for item in payload["items"]}

        assert len(items) == 12
        assert items["market_cn"]["status"] == "healthy"
        assert items["market_us"]["status"] == "failed"
        assert items["market_hk"]["status"] == "not_recorded"
        assert items["evidence_incremental"]["status"] == "running"
        assert items["evidence_incremental"]["progress"]["current"] == 8
        assert items["fundamental_shard"]["status"] == "stalled"
        assert items["eastmoney_calendar"]["status"] == "not_recorded"
        assert items["market_us"]["error_summary"] == "Latest task run failed."
        assert items["market_us"]["provider"] == "configured"
        assert "password" not in str(payload)
        assert session.get(TaskRun, shard.id).status == "running"
        assert payload["summary"] == {
                "total": 12,
            "running": 1,
            "healthy": 1,
                "attention": 10,
            "recent_failures": 1,
        }
    finally:
        session.close()


def test_monitor_marks_old_success_overdue_and_bounds_untrusted_progress():
    session = _session()
    try:
        run = _run(
            task_name="ingestion.sync_instrument_universe",
            status="succeeded",
            input_json={"market": "CN", "provider": "akshare"},
            age=timedelta(days=5),
            result_json={
                "progress": {
                    "phase": "x" * 300,
                    "current": -1,
                    "total": 10,
                    "message": "secret" * 100,
                }
            },
        )
        session.add(run)
        session.commit()

        item = next(
            item
            for item in get_crawler_monitor(session, now=NOW)["items"]
            if item["id"] == "universe_cn"
        )

        assert item["status"] == "overdue"
        assert item["diagnostic_code"] == "freshness_window_exceeded"
        assert item["progress"] is None
    finally:
        session.close()
