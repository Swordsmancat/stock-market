from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from packages.services.task_runs import (
    get_latest_task_run_payload,
    get_recent_task_runs_payload,
    get_task_run_payload,
    retry_task_run_payload,
)
from packages.shared.database import get_session

router = APIRouter(prefix="/task-runs", tags=["task-runs"])


@router.get("/recent")
def get_recent_task_runs(
    limit: int = Query(default=10, ge=1, le=100),
    status: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return get_recent_task_runs_payload(session=session, limit=limit, status=status)


@router.get("/latest")
def get_latest_task_run(
    task_name: str = Query(...),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return get_latest_task_run_payload(session=session, task_name=task_name)


@router.get("/{task_run_id}")
def get_task_run(task_run_id: str, session: Session = Depends(get_session)) -> dict[str, object]:
    payload = get_task_run_payload(session=session, task_run_id=task_run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Task run not found")
    return payload


@router.post("/{task_run_id}/retry")
def retry_task_run(task_run_id: str, session: Session = Depends(get_session)) -> dict[str, object]:
    payload = retry_task_run_payload(session=session, task_run_id=task_run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Task run not found")
    return payload
