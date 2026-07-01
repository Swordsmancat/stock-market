from datetime import datetime, timezone

from sqlalchemy.orm import Session

from packages.domain.models import TaskRun


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _duration_ms(started_at: datetime, finished_at: datetime) -> int:
    return max(0, int((finished_at - started_at).total_seconds() * 1000))


def _serialize_task_run(task_run: TaskRun) -> dict[str, object]:
    started_at = _as_utc(task_run.started_at)
    finished_at = _as_utc(task_run.finished_at)
    created_at = _as_utc(task_run.created_at)
    return {
        "id": str(task_run.id),
        "task_name": task_run.task_name,
        "status": task_run.status,
        "started_at": started_at.isoformat() if started_at is not None else None,
        "finished_at": finished_at.isoformat() if finished_at is not None else None,
        "duration_ms": task_run.duration_ms,
        "input_json": task_run.input_json,
        "result_json": task_run.result_json,
        "error_message": task_run.error_message,
        "created_at": created_at.isoformat() if created_at is not None else None,
    }


def start_task_run(task_name: str, input_json: dict, session: Session) -> TaskRun:
    now = _utc_now()
    task_run = TaskRun(
        task_name=task_name,
        status="running",
        started_at=now,
        input_json=input_json,
        created_at=now,
    )
    session.add(task_run)
    session.commit()
    return task_run


def finish_task_run(task_run: TaskRun, result_json: dict, session: Session) -> dict[str, object]:
    finished_at = _utc_now()
    started_at = _as_utc(task_run.started_at) or finished_at
    task_run.status = "succeeded"
    task_run.finished_at = finished_at
    task_run.duration_ms = _duration_ms(started_at, finished_at)
    task_run.result_json = result_json
    task_run.error_message = None
    session.commit()
    return _serialize_task_run(task_run)


def fail_task_run(task_run: TaskRun, error_message: str, session: Session) -> dict[str, object]:
    finished_at = _utc_now()
    started_at = _as_utc(task_run.started_at) or finished_at
    task_run.status = "failed"
    task_run.finished_at = finished_at
    task_run.duration_ms = _duration_ms(started_at, finished_at)
    task_run.error_message = error_message
    session.commit()
    return _serialize_task_run(task_run)


def get_recent_task_runs_payload(
    session: Session,
    limit: int = 10,
    status: str | None = None,
) -> dict[str, object]:
    query = session.query(TaskRun)
    if status:
        query = query.filter(TaskRun.status == status)
    rows = query.order_by(TaskRun.started_at.desc()).limit(limit).all()
    return {"source": "database", "items": [_serialize_task_run(row) for row in rows]}


def get_latest_task_run_payload(session: Session, task_name: str) -> dict[str, object]:
    task_run = (
        session.query(TaskRun)
        .filter(TaskRun.task_name == task_name)
        .order_by(TaskRun.started_at.desc())
        .first()
    )
    if task_run is None:
        return {"task_name": task_name, "status": "not_found", "source": "database"}
    return {**_serialize_task_run(task_run), "source": "database"}
