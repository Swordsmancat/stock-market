from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from packages.domain.models import TaskRun
from packages.services.task_dispatch import is_dispatchable_task
from packages.shared.config import settings


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
        "celery_task_id": task_run.celery_task_id,
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


def update_task_run_progress(
    task_run: TaskRun,
    *,
    phase: str,
    current: int,
    total: int,
    message: str,
    session: Session,
) -> dict[str, object]:
    if task_run.status != "running":
        raise ValueError("Task run progress can only be updated while the task is running.")
    bounded_total = max(0, total)
    bounded_current = max(0, min(current, bounded_total)) if bounded_total else 0
    task_run.result_json = {
        **(task_run.result_json or {}),
        "progress": {
            "phase": phase,
            "current": bounded_current,
            "total": bounded_total,
            "message": message,
            "updated_at": _utc_now().isoformat(),
        },
    }
    session.commit()
    session.refresh(task_run)
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


def expire_stale_task_runs(session: Session, timeout_minutes: int | None = None) -> int:
    cutoff = _utc_now() - timedelta(minutes=timeout_minutes or settings.task_run_stale_minutes)
    stale_runs = (
        session.query(TaskRun)
        .filter(TaskRun.status == "running")
        .filter(TaskRun.started_at < cutoff)
        .all()
    )
    for task_run in stale_runs:
        fail_task_run(task_run, "Task run timed out while waiting for worker", session=session)
    return len(stale_runs)


def enqueue_task_run(task_name: str, input_json: dict, session: Session) -> dict[str, object]:
    from packages.services.task_dispatch import dispatch_task_run

    expire_stale_task_runs(session)
    task_run = start_task_run(task_name, input_json, session=session)

    if not is_dispatchable_task(task_name):
        fail_task_run(
            task_run,
            f"Task '{task_name}' is not configured for Celery dispatch",
            session=session,
        )
        return {
            "source": "database",
            "status": "dispatch_failed",
            "task_run": _serialize_task_run(task_run),
        }

    try:
        celery_task_id = dispatch_task_run(task_name, input_json, str(task_run.id))
    except Exception as exc:
        fail_task_run(task_run, f"Failed to dispatch Celery task: {exc}", session=session)
        return {
            "source": "database",
            "status": "dispatch_failed",
            "task_run": _serialize_task_run(session.get(TaskRun, task_run.id) or task_run),
            "error": str(exc),
        }

    updated_task_run = session.get(TaskRun, task_run.id)
    if updated_task_run is None:
        msg = f"Task run not found after dispatch: {task_run.id}"
        raise RuntimeError(msg)
    updated_task_run.celery_task_id = celery_task_id
    session.commit()
    session.refresh(updated_task_run)
    return {
        "source": "database",
        "status": "dispatched",
        "task_run": _serialize_task_run(updated_task_run),
        "celery_task_id": celery_task_id,
    }


def get_task_run_payload(session: Session, task_run_id: str) -> dict[str, object] | None:
    expire_stale_task_runs(session)
    try:
        task_run_uuid = UUID(task_run_id)
    except ValueError:
        return None
    task_run = session.get(TaskRun, task_run_uuid)
    if task_run is None:
        return None
    return {"source": "database", "item": _serialize_task_run(task_run)}


def get_recent_task_runs_payload(
    session: Session,
    limit: int = 10,
    status: str | None = None,
) -> dict[str, object]:
    expire_stale_task_runs(session)
    query = session.query(TaskRun)
    if status:
        query = query.filter(TaskRun.status == status)
    rows = query.order_by(TaskRun.started_at.desc()).limit(limit).all()
    return {"source": "database", "items": [_serialize_task_run(row) for row in rows]}


def get_latest_task_run_payload(session: Session, task_name: str) -> dict[str, object]:
    expire_stale_task_runs(session)
    task_run = (
        session.query(TaskRun)
        .filter(TaskRun.task_name == task_name)
        .order_by(TaskRun.started_at.desc())
        .first()
    )
    if task_run is None:
        return {"task_name": task_name, "status": "not_found", "source": "database"}
    return {**_serialize_task_run(task_run), "source": "database"}


def retry_task_run_payload(session: Session, task_run_id: str) -> dict[str, object] | None:
    try:
        task_run_uuid = UUID(task_run_id)
    except ValueError:
        return None

    original = session.get(TaskRun, task_run_uuid)
    if original is None:
        return None

    retry_input = {
        **(original.input_json or {}),
        "retry_of": str(original.id),
    }
    result = enqueue_task_run(original.task_name, retry_input, session=session)
    if result["status"] == "dispatched":
        return {
            **result,
            "status": "retry_started",
            "item": result["task_run"],
        }
    return {
        **result,
        "status": "retry_dispatch_failed",
        "item": result["task_run"],
    }
