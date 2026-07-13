"""Read-only diagnostics for TaskRun reliability state."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import and_, create_engine, or_
from sqlalchemy.orm import Session, sessionmaker

from packages.domain.models import TaskRun
from packages.shared.config import settings


OK_STATUS = "OK"
WARN_STATUS = "WARN"
DEFAULT_RECENT_LIMIT = 10


@dataclass(frozen=True)
class TaskRunHealthResult:
    status: str
    message: str
    recent_count: int = 0
    stale_running_count: int = 0
    failed_last_24h_count: int = 0
    stale_task_names: list[str] = field(default_factory=list)
    failed_task_names: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _summarize_task_names(task_runs: Iterable[TaskRun]) -> list[str]:
    task_name_counts = Counter(task_run.task_name for task_run in task_runs)
    return [
        f"{task_name} ({count})" if count > 1 else task_name
        for task_name, count in sorted(task_name_counts.items())
    ]


def _format_exception(error: BaseException) -> str:
    return " ".join(str(error).split())


def create_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    engine = create_engine(database_url or settings.database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def check_task_run_health(
    session: Session,
    now: datetime | None = None,
    stale_minutes: int | None = None,
    recent_limit: int = DEFAULT_RECENT_LIMIT,
) -> TaskRunHealthResult:
    current_time = _as_utc(now or _utc_now())
    stale_cutoff = current_time - timedelta(minutes=stale_minutes or settings.task_run_stale_minutes)
    failed_cutoff = current_time - timedelta(hours=24)

    try:
        recent_task_runs = (
            session.query(TaskRun)
            .order_by(TaskRun.started_at.desc())
            .limit(recent_limit)
            .all()
        )
        stale_running_task_runs = (
            session.query(TaskRun)
            .filter(TaskRun.status == "running")
            .filter(
                or_(
                    and_(TaskRun.heartbeat_at.is_(None), TaskRun.started_at < stale_cutoff),
                    TaskRun.heartbeat_at < stale_cutoff,
                )
            )
            .order_by(TaskRun.started_at.asc())
            .all()
        )
        failed_task_runs = (
            session.query(TaskRun)
            .filter(TaskRun.status == "failed")
            .filter(
                or_(
                    TaskRun.finished_at >= failed_cutoff,
                    and_(TaskRun.finished_at.is_(None), TaskRun.started_at >= failed_cutoff),
                )
            )
            .order_by(TaskRun.started_at.desc())
            .all()
        )
    except Exception as exc:
        return TaskRunHealthResult(
            status=WARN_STATUS,
            message="TaskRun database unavailable",
            details=[_format_exception(exc)],
        )

    if not recent_task_runs:
        return TaskRunHealthResult(
            status=OK_STATUS,
            message="no task runs found",
            recent_count=0,
        )

    stale_task_names = _summarize_task_names(stale_running_task_runs)
    failed_task_names = _summarize_task_names(failed_task_runs)
    details = [f"recent_task_runs={len(recent_task_runs)}"]

    if stale_running_task_runs:
        details.append(
            f"stale_running={len(stale_running_task_runs)} names={', '.join(stale_task_names)}"
        )
    if failed_task_runs:
        details.append(
            f"failed_last_24h={len(failed_task_runs)} names={', '.join(failed_task_names)}"
        )

    if stale_running_task_runs or failed_task_runs:
        return TaskRunHealthResult(
            status=WARN_STATUS,
            message="TaskRun warnings detected",
            recent_count=len(recent_task_runs),
            stale_running_count=len(stale_running_task_runs),
            failed_last_24h_count=len(failed_task_runs),
            stale_task_names=stale_task_names,
            failed_task_names=failed_task_names,
            details=details,
        )

    return TaskRunHealthResult(
        status=OK_STATUS,
        message="no stale running or recently failed task runs found",
        recent_count=len(recent_task_runs),
        details=details,
    )


def render_result(result: TaskRunHealthResult) -> str:
    lines = [f"{result.status}: {result.message}"]
    lines.extend(f"  - {detail}" for detail in result.details)
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check TaskRun reliability state without writing data.")
    parser.add_argument(
        "--stale-minutes",
        type=int,
        default=None,
        help="running TaskRun age threshold; defaults to TASK_RUN_STALE_MINUTES/settings value",
    )
    parser.add_argument(
        "--recent-limit",
        type=int,
        default=DEFAULT_RECENT_LIMIT,
        help="number of recent TaskRun rows to query for the summary",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        session_factory = create_session_factory()
        with session_factory() as session:
            result = check_task_run_health(
                session,
                stale_minutes=args.stale_minutes,
                recent_limit=args.recent_limit,
            )
    except Exception as exc:
        result = TaskRunHealthResult(
            status=WARN_STATUS,
            message="TaskRun database unavailable",
            details=[_format_exception(exc)],
        )

    print(render_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
