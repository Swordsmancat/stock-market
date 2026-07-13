from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from apps.worker.celery_app import celery_app
from packages.domain.models import TaskRun
from packages.services.daily_research_loop import (
    DAILY_RESEARCH_LOOP_TASK_NAME,
    DailyResearchLoopInput,
    DailyResearchLoopExecutionError,
    run_daily_research_loop,
)
from packages.services.task_runs import (
    fail_task_run,
    finish_task_run,
    start_task_run,
    update_task_run_progress,
)
from packages.shared.config import settings
from packages.shared.database import SessionLocal


class DailyResearchLoopPartialFailure(RuntimeError):
    pass


@celery_app.task(name=DAILY_RESEARCH_LOOP_TASK_NAME)
def run_daily_research_loop_task(
    market: str = "CN",
    asset_type: str = "stock",
    profile_id: str = "balanced_research",
    shortlist_limit: int = 10,
    locale: str = "zh",
    use_llm: bool = True,
    outcome_run_limit: int | None = None,
    trigger: str = "scheduled",
    task_run_id: str | None = None,
) -> dict[str, object]:
    session = SessionLocal()
    input_json = {
        "market": market,
        "asset_type": asset_type,
        "profile_id": profile_id,
        "shortlist_limit": shortlist_limit,
        "locale": locale,
        "use_llm": use_llm,
        "outcome_run_limit": (
            settings.daily_research_loop_outcome_run_limit
            if outcome_run_limit is None
            else outcome_run_limit
        ),
        "trigger": trigger,
    }

    try:
        task_run, replay_result = _load_or_start_task_run(
            session=session,
            task_run_id=task_run_id,
            input_json=input_json,
        )
        if replay_result is not None:
            return replay_result

        last_progress: dict[str, object] | None = None

        def report_progress(phase: str, current: int, total: int, message: str) -> None:
            nonlocal last_progress
            payload = update_task_run_progress(
                task_run,
                phase=phase,
                current=current,
                total=total,
                message=message,
                session=session,
            )
            result_json = payload.get("result_json")
            if isinstance(result_json, dict) and isinstance(
                result_json.get("progress"),
                dict,
            ):
                last_progress = dict(result_json["progress"])

        try:
            result = run_daily_research_loop(
                DailyResearchLoopInput(
                    market=market,
                    asset_type=asset_type,
                    profile_id=profile_id,
                    shortlist_limit=shortlist_limit,
                    locale="en" if locale == "en" else "zh",
                    use_llm=use_llm,
                    outcome_run_limit=input_json["outcome_run_limit"],
                ),
                session=session,
                task_run_id=task_run.id,
                progress=report_progress,
            )
            result = _with_progress(result, last_progress)
            if result.get("status") == "partial_failure":
                task_run.result_json = result
                session.commit()
                failed_count = int(
                    (result.get("outcomes") or {}).get("failed_run_count") or 0
                )
                raise DailyResearchLoopPartialFailure(
                    f"Daily research outcome evaluation failed for {failed_count} cohort(s)."
                )
            finish_task_run(task_run, result, session=session)
            return result
        except Exception as exc:
            session.rollback()
            current_task_run = session.get(TaskRun, task_run.id) or task_run
            if isinstance(exc, DailyResearchLoopExecutionError):
                current_task_run.result_json = _with_progress(
                    exc.partial_result,
                    last_progress,
                )
            if current_task_run.status == "running":
                fail_task_run(
                    current_task_run,
                    _task_failure_message(exc),
                    session=session,
                )
            raise
    finally:
        session.close()


def _load_or_start_task_run(
    *,
    session: Session,
    task_run_id: str | None,
    input_json: dict[str, object],
) -> tuple[TaskRun, dict[str, object] | None]:
    if not task_run_id:
        return (
            start_task_run(
                DAILY_RESEARCH_LOOP_TASK_NAME,
                input_json,
                session=session,
            ),
            None,
        )
    try:
        parsed_task_run_id = UUID(task_run_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid task_run_id.") from exc
    task_run = session.get(TaskRun, parsed_task_run_id)
    if task_run is None:
        raise ValueError(f"Task run not found: {task_run_id}")
    if task_run.task_name != DAILY_RESEARCH_LOOP_TASK_NAME:
        raise ValueError("Task run belongs to another task.")
    if task_run.status == "succeeded":
        if not isinstance(task_run.result_json, dict):
            raise ValueError("Succeeded daily research TaskRun has no result payload.")
        return task_run, dict(task_run.result_json)
    if task_run.status != "running":
        raise ValueError("Daily research TaskRun is not running.")
    return task_run, None


def _task_failure_message(exc: Exception) -> str:
    if isinstance(exc, DailyResearchLoopPartialFailure):
        return str(exc)
    if isinstance(exc, DailyResearchLoopExecutionError):
        return f"Daily research loop failed during {exc.phase} ({exc.error_type})."
    return f"Daily research loop failed ({type(exc).__name__})."


def _with_progress(
    result: dict[str, object],
    progress: dict[str, object] | None,
) -> dict[str, object]:
    if progress is None:
        return result
    return {**result, "progress": dict(progress)}
