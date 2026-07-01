from datetime import date, timedelta
from uuid import UUID

from apps.worker.celery_app import celery_app
from packages.domain.models import TaskRun
from packages.services.ingestion import ingest_market_snapshot
from packages.services.task_runs import fail_task_run, finish_task_run, start_task_run
from packages.shared.config import settings
from packages.shared.database import SessionLocal


@celery_app.task(name="ingestion.ingest_market_data")
def ingest_market_data(
    market: str,
    start: str | None = None,
    end: str | None = None,
    provider: str | None = None,
    task_run_id: str | None = None,
) -> dict[str, object]:
    end_date = date.fromisoformat(end) if end else date.today()
    start_date = date.fromisoformat(start) if start else end_date - timedelta(days=2)
    provider_value = provider or settings.market_data_provider
    session = SessionLocal()

    if task_run_id:
        task_run = session.get(TaskRun, UUID(task_run_id))
        if task_run is None:
            session.close()
            msg = f"Task run not found: {task_run_id}"
            raise ValueError(msg)
    else:
        task_run = start_task_run(
            "ingestion.ingest_market_data",
            {
                "market": market,
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "provider": provider_value,
            },
            session=session,
        )

    try:
        snapshot = ingest_market_snapshot(
            market,
            start_date,
            end_date,
            session=session,
            provider_name=provider_value,
        )
        result_payload = {
            "market": str(snapshot["market"]),
            "instrument_count": int(snapshot["instrument_count"]),
            "bar_count": int(snapshot["bar_count"]),
            "status": str(snapshot["status"]),
            "provider": provider_value,
        }
        finish_task_run(task_run, result_payload, session=session)
        return result_payload
    except Exception as exc:
        fail_task_run(task_run, str(exc), session=session)
        raise
    finally:
        session.close()


@celery_app.task(name="ingestion.ingest_mock_market_data")
def ingest_mock_market_data(
    market: str,
    start: str | None = None,
    end: str | None = None,
    provider: str | None = None,
) -> dict[str, int | str]:
    return ingest_market_data(
        market=market,
        start=start,
        end=end,
        provider=provider or "mock",
    )
