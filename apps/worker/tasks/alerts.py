from uuid import UUID

from apps.worker.celery_app import celery_app
from packages.domain.models import TaskRun
from packages.services.platform_settings import get_effective_market_data_provider
from packages.services.task_runs import fail_task_run, finish_task_run, start_task_run
from packages.services.watchlist_alerts import (
    build_no_alert_rules_result,
    evaluate_all_watchlist_alerts,
    has_actionable_watchlist_alerts,
)
from packages.shared.database import SessionLocal


@celery_app.task(name="alerts.evaluate_watchlist_alerts")
def evaluate_watchlist_alerts(
    provider: str | None = None,
    task_run_id: str | None = None,
) -> dict[str, object]:
    provider_value = get_effective_market_data_provider(provider)
    session = SessionLocal()

    try:
        if task_run_id is None:
            try:
                has_actionable_alerts = has_actionable_watchlist_alerts(session)
            except Exception:
                session.rollback()
            else:
                if not has_actionable_alerts:
                    return build_no_alert_rules_result()

        if task_run_id:
            task_run = session.get(TaskRun, UUID(task_run_id))
            if task_run is None:
                msg = f"Task run not found: {task_run_id}"
                raise ValueError(msg)
        else:
            task_run = start_task_run(
                "alerts.evaluate_watchlist_alerts",
                {"provider": provider_value},
                session=session,
            )

        try:
            result = evaluate_all_watchlist_alerts(session=session, provider_name=provider_value)
            finish_task_run(task_run, result, session=session)
            return result
        except Exception as exc:
            fail_task_run(task_run, str(exc), session=session)
            raise
    finally:
        session.close()
