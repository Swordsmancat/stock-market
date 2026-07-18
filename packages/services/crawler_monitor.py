from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Literal

from sqlalchemy.orm import Session

from packages.domain.models import TaskRun


CrawlerStatus = Literal[
    "running",
    "healthy",
    "overdue",
    "stalled",
    "failed",
    "not_recorded",
]

MAX_RECENT_TASK_RUNS = 2_000
RECENT_FAILURE_WINDOW = timedelta(hours=24)
MAX_PROGRESS_TEXT = 160
SAFE_PROVIDER_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


@dataclass(frozen=True)
class CrawlerPipeline:
    id: str
    task_name: str
    selector: tuple[tuple[str, str], ...]
    scope: str
    provider: str
    cadence: str
    freshness: timedelta
    stall_after: timedelta


PIPELINES: tuple[CrawlerPipeline, ...] = (
    CrawlerPipeline(
        "market_cn",
        "ingestion.ingest_market_data",
        (("market", "CN"),),
        "CN",
        "configured",
        "daily",
        timedelta(hours=72),
        timedelta(minutes=45),
    ),
    CrawlerPipeline(
        "market_us",
        "ingestion.ingest_market_data",
        (("market", "US"),),
        "US",
        "configured",
        "daily",
        timedelta(hours=72),
        timedelta(minutes=45),
    ),
    CrawlerPipeline(
        "market_hk",
        "ingestion.ingest_market_data",
        (("market", "HK"),),
        "HK",
        "configured",
        "daily",
        timedelta(hours=72),
        timedelta(minutes=45),
    ),
    CrawlerPipeline(
        "universe_cn",
        "ingestion.sync_instrument_universe",
        (("market", "CN"),),
        "CN instruments",
        "akshare",
        "daily",
        timedelta(hours=72),
        timedelta(hours=2),
    ),
    CrawlerPipeline(
        "evidence_incremental",
        "ingestion.backfill_a_share_research_evidence",
        (("run_kind", "incremental"),),
        "A-share evidence",
        "multi_source",
        "weekdays",
        timedelta(hours=96),
        timedelta(minutes=30),
    ),
    CrawlerPipeline(
        "fundamental_shard",
        "ingestion.backfill_a_share_research_evidence",
        (("run_kind", "fundamental_shard"),),
        "A-share fundamentals",
        "akshare",
        "weekdays",
        timedelta(hours=96),
        timedelta(minutes=30),
    ),
    CrawlerPipeline(
        "official_disclosures",
        "ingestion.ingest_watchlist_official_disclosures",
        (),
        "Watchlist disclosures",
        "cninfo",
        "hourly",
        timedelta(hours=3),
        timedelta(minutes=30),
    ),
    CrawlerPipeline(
        "eastmoney_calendar",
        "ingestion.refresh_eastmoney_economic_calendar",
        (),
        "Economic calendar",
        "eastmoney_public",
        "daily",
        timedelta(hours=36),
        timedelta(minutes=15),
    ),
    CrawlerPipeline(
        "eastmoney_industry",
        "ingestion.refresh_eastmoney_industry_rankings",
        (),
        "Industry history",
        "eastmoney_public",
        "weekdays",
        timedelta(hours=72),
        timedelta(minutes=30),
    ),
    CrawlerPipeline(
        "eastmoney_news",
        "ingestion.refresh_eastmoney_research_news",
        (),
        "Research news",
        "eastmoney_public",
        "hourly",
        timedelta(hours=3),
        timedelta(minutes=30),
    ),
    CrawlerPipeline(
        "eastmoney_fundamentals",
        "ingestion.refresh_eastmoney_research_fundamentals",
        (),
        "Research fundamentals",
        "eastmoney_public",
        "weekdays",
        timedelta(hours=72),
        timedelta(minutes=45),
    ),
)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    normalized = _as_utc(value)
    return normalized.isoformat() if normalized is not None else None


def _matches(task_run: TaskRun, pipeline: CrawlerPipeline) -> bool:
    if task_run.task_name != pipeline.task_name:
        return False
    input_json = task_run.input_json if isinstance(task_run.input_json, dict) else {}
    return all(input_json.get(key) == value for key, value in pipeline.selector)


def _classify(
    task_run: TaskRun | None,
    pipeline: CrawlerPipeline,
    now: datetime,
) -> tuple[CrawlerStatus, str | None]:
    if task_run is None:
        return "not_recorded", None

    status = task_run.status
    if status == "running":
        activity_at = _as_utc(task_run.heartbeat_at) or _as_utc(task_run.started_at)
        if activity_at is None or now - activity_at > pipeline.stall_after:
            return "stalled", "stale_heartbeat"
        return "running", None
    if status == "failed":
        return "failed", "task_run_failed"
    if status == "succeeded":
        completed_at = _as_utc(task_run.finished_at) or _as_utc(task_run.started_at)
        if completed_at is None or now - completed_at > pipeline.freshness:
            return "overdue", "freshness_window_exceeded"
        return "healthy", None
    return "failed", "unsupported_task_run_status"


def _bounded_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split())
    if not normalized:
        return None
    return normalized[:MAX_PROGRESS_TEXT]


def _safe_provider(value: object, fallback: str) -> str:
    if isinstance(value, str) and SAFE_PROVIDER_PATTERN.fullmatch(value):
        return value
    return fallback


def _bounded_integer(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _progress(task_run: TaskRun | None) -> dict[str, object] | None:
    if task_run is None or not isinstance(task_run.result_json, dict):
        return None
    raw = task_run.result_json.get("progress")
    if not isinstance(raw, dict):
        return None
    current = _bounded_integer(raw.get("current"))
    total = _bounded_integer(raw.get("total"))
    if current is None or total is None:
        return None
    return {
        "phase": _bounded_text(raw.get("phase")),
        "current": min(current, total) if total else 0,
        "total": total,
        "message": _bounded_text(raw.get("message")),
        "updated_at": _bounded_text(raw.get("updated_at")),
    }


def _duration_ms(task_run: TaskRun | None, now: datetime) -> int | None:
    if task_run is None:
        return None
    if task_run.duration_ms is not None:
        return max(0, task_run.duration_ms)
    started_at = _as_utc(task_run.started_at)
    if started_at is None:
        return None
    ended_at = _as_utc(task_run.finished_at) or now
    return max(0, int((ended_at - started_at).total_seconds() * 1_000))


def get_crawler_monitor(
    session: Session,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    generated_at = _as_utc(now) or datetime.now(timezone.utc)
    task_names = sorted({pipeline.task_name for pipeline in PIPELINES})
    recent_runs = (
        session.query(TaskRun)
        .filter(TaskRun.task_name.in_(task_names))
        .order_by(TaskRun.started_at.desc())
        .limit(MAX_RECENT_TASK_RUNS)
        .all()
    )

    items: list[dict[str, object]] = []
    for pipeline in PIPELINES:
        matching = [run for run in recent_runs if _matches(run, pipeline)]
        latest = matching[0] if matching else None
        status, diagnostic_code = _classify(latest, pipeline, generated_at)
        failure_count = sum(
            1
            for run in matching
            if run.status == "failed"
            and (
                _as_utc(run.finished_at)
                or _as_utc(run.started_at)
                or datetime.min.replace(tzinfo=timezone.utc)
            )
            >= generated_at - RECENT_FAILURE_WINDOW
        )
        input_json = (
            latest.input_json if latest is not None and isinstance(latest.input_json, dict) else {}
        )
        provider = _safe_provider(input_json.get("provider"), pipeline.provider)
        items.append(
            {
                "id": pipeline.id,
                "status": status,
                "task_name": pipeline.task_name,
                "scope": pipeline.scope,
                "provider": provider,
                "cadence": pipeline.cadence,
                "latest_task_run_id": str(latest.id) if latest is not None else None,
                "started_at": _iso(latest.started_at) if latest is not None else None,
                "finished_at": _iso(latest.finished_at) if latest is not None else None,
                "heartbeat_at": _iso(latest.heartbeat_at) if latest is not None else None,
                "duration_ms": _duration_ms(latest, generated_at),
                "progress": _progress(latest),
                "recent_failure_count": failure_count,
                "diagnostic_code": diagnostic_code,
                "error_summary": "Latest task run failed." if status == "failed" else None,
            }
        )

    status_counts = {
        status: 0
        for status in ("running", "healthy", "overdue", "stalled", "failed", "not_recorded")
    }
    for item in items:
        status_counts[str(item["status"])] += 1

    return {
        "status": "ok",
        "generated_at": generated_at.isoformat(),
        "summary": {
            "total": len(items),
            "running": status_counts["running"],
            "healthy": status_counts["healthy"],
            "attention": sum(
                status_counts[key] for key in ("overdue", "stalled", "failed", "not_recorded")
            ),
            "recent_failures": sum(int(item["recent_failure_count"]) for item in items),
        },
        "items": items,
    }
