from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from packages.services.research_evidence_backfill import (
    resolve_completed_daily_bar_watermark,
)
from packages.services.research_shortlist_outcomes import (
    evaluate_due_research_shortlist_outcomes,
)
from packages.services.research_shortlists import (
    ResearchShortlistGenerateInput,
    ResearchShortlistReadinessError,
    generate_research_shortlist,
)


DAILY_RESEARCH_LOOP_TASK_NAME = "research.run_daily_research_loop"
MAX_DETAIL_ITEMS = 20
MAX_DETAIL_KEYS = 50
MAX_DETAIL_STRING_LENGTH = 256
SAFETY_PAYLOAD = {
    "research_signal_only": True,
    "no_automated_trading": True,
    "outcomes_do_not_change_shortlist_ranking": True,
}

DailyResearchProgressCallback = Callable[[str, int, int, str], None]


class DailyResearchLoopExecutionError(RuntimeError):
    def __init__(
        self,
        phase: str,
        *,
        error_type: str,
        partial_result: dict[str, object],
    ) -> None:
        super().__init__(f"Daily research loop failed during {phase}.")
        self.phase = phase
        self.error_type = error_type[:128]
        self.partial_result = partial_result


@dataclass(frozen=True)
class DailyResearchLoopInput:
    market: str = "CN"
    asset_type: str = "stock"
    profile_id: str = "balanced_research"
    shortlist_limit: int = 10
    locale: Literal["zh", "en"] = "zh"
    use_llm: bool = True
    outcome_run_limit: int = 25


def run_daily_research_loop(
    payload: DailyResearchLoopInput,
    *,
    session: Session,
    task_run_id: str | UUID,
    now: datetime | None = None,
    progress: DailyResearchProgressCallback | None = None,
) -> dict[str, object]:
    normalized = _normalize_input(payload)
    parsed_task_run_id = _parse_uuid(task_run_id, label="task_run_id")

    try:
        _report_progress(progress, "watermark", 0, 3, "Resolving completed A-share bars.")
        watermark = resolve_completed_daily_bar_watermark(
            session=session,
            market=normalized.market,
            provider="akshare",
            now=now,
        )
    except Exception as exc:
        partial_result = _base_result(
            status="failed",
            watermark=_failed_phase("WATERMARK_RESOLUTION_FAILED", exc),
            outcomes=_skipped_phase("WATERMARK_FAILED"),
            publication=_skipped_phase("WATERMARK_FAILED"),
        )
        raise _execution_error("watermark", exc, partial_result) from exc
    if watermark.get("status") != "ready":
        result = _base_result(
            status="deferred",
            watermark=watermark,
            outcomes=_skipped_phase("WATERMARK_NOT_READY"),
            publication=_skipped_phase("WATERMARK_NOT_READY"),
        )
        try:
            _report_progress(
                progress,
                "completed",
                3,
                3,
                "Daily research evidence is not ready.",
            )
        except Exception as exc:
            raise _execution_error("completion", exc, result) from exc
        return result

    try:
        completed_through = _watermark_date(watermark)
    except Exception as exc:
        invalid_watermark = {
            **watermark,
            "status": "failed",
            "code": "INVALID_DAILY_BAR_WATERMARK",
            "error_type": type(exc).__name__[:128],
        }
        partial_result = _base_result(
            status="failed",
            watermark=invalid_watermark,
            outcomes=_skipped_phase("WATERMARK_FAILED"),
            publication=_skipped_phase("WATERMARK_FAILED"),
        )
        raise _execution_error("watermark", exc, partial_result) from exc
    try:
        _report_progress(progress, "outcomes", 1, 3, "Evaluating due research cohorts.")
        outcomes = evaluate_due_research_shortlist_outcomes(
            session=session,
            market=normalized.market,
            profile_id=normalized.profile_id,
            verified_completed_through=completed_through,
            evaluation_task_run_id=parsed_task_run_id,
            run_limit=normalized.outcome_run_limit,
            now=now,
            progress=progress,
        )
    except Exception as exc:
        partial_result = _base_result(
            status="failed",
            watermark=watermark,
            outcomes=_failed_phase("OUTCOME_BATCH_FAILED", exc),
            publication=_skipped_phase("OUTCOME_BATCH_FAILED"),
        )
        raise _execution_error("outcomes", exc, partial_result) from exc

    try:
        _report_progress(
            progress,
            "publication",
            2,
            3,
            "Publishing the verified daily shortlist.",
        )
        publication = _publish_shortlist(
            normalized,
            completed_through=completed_through,
            task_run_id=parsed_task_run_id,
            session=session,
        )
    except Exception as exc:
        partial_result = _base_result(
            status="failed",
            watermark=watermark,
            outcomes=outcomes,
            publication=_failed_phase("SHORTLIST_PUBLICATION_FAILED", exc),
        )
        raise _execution_error("publication", exc, partial_result) from exc

    failed_run_count = int(outcomes.get("failed_run_count") or 0)
    if failed_run_count:
        status = "partial_failure"
    elif publication.get("status") == "deferred":
        status = "completed_with_deferred_generation"
    else:
        status = "completed"

    result = _base_result(
        status=status,
        watermark=watermark,
        outcomes=outcomes,
        publication=publication,
    )
    try:
        _report_progress(progress, "completed", 3, 3, "Daily research loop finished.")
    except Exception as exc:
        raise _execution_error("completion", exc, result) from exc
    return result


def _normalize_input(payload: DailyResearchLoopInput) -> DailyResearchLoopInput:
    market = payload.market.strip().upper()
    if market != "CN":
        raise ValueError(f"Unsupported daily research market: {payload.market}")
    asset_type = payload.asset_type.strip().lower()
    if asset_type != "stock":
        raise ValueError(f"Unsupported daily research asset type: {payload.asset_type}")
    profile_id = payload.profile_id.strip().lower()
    if not profile_id:
        raise ValueError("Daily research profile_id is required.")
    if not 1 <= payload.shortlist_limit <= 20:
        raise ValueError("Daily research shortlist_limit must be between 1 and 20.")
    if not 1 <= payload.outcome_run_limit <= 100:
        raise ValueError("Daily research outcome_run_limit must be between 1 and 100.")
    return DailyResearchLoopInput(
        market=market,
        asset_type=asset_type,
        profile_id=profile_id,
        shortlist_limit=payload.shortlist_limit,
        locale="en" if payload.locale == "en" else "zh",
        use_llm=bool(payload.use_llm),
        outcome_run_limit=payload.outcome_run_limit,
    )


def _publish_shortlist(
    payload: DailyResearchLoopInput,
    *,
    completed_through: date,
    task_run_id: UUID,
    session: Session,
) -> dict[str, object]:
    try:
        response = generate_research_shortlist(
            ResearchShortlistGenerateInput(
                profile_id=payload.profile_id,
                market=payload.market,
                asset_type=payload.asset_type,
                shortlist_limit=payload.shortlist_limit,
                locale=payload.locale,
                use_llm=payload.use_llm,
                verified_decision_date=completed_through,
                generation_task_run_id=task_run_id,
            ),
            session=session,
        )
    except ResearchShortlistReadinessError as exc:
        if session.in_transaction():
            session.rollback()
        return {
            "status": "deferred",
            "code": exc.code,
            "details": _bounded_detail_value(exc.details),
        }

    run = response.get("run") if isinstance(response.get("run"), dict) else {}
    items = response.get("items") if isinstance(response.get("items"), list) else []
    if (
        response.get("status") != "ok"
        or not run.get("id")
        or run.get("decision_date") != completed_through.isoformat()
    ):
        raise RuntimeError(
            "Research shortlist publication returned an invalid verified-date result."
        )
    original_task_run_id = run.get("generation_task_run_id")
    return {
        "status": "created" if original_task_run_id == str(task_run_id) else "reused",
        "shortlist_run_id": run.get("id"),
        "generation_task_run_id": original_task_run_id,
        "generation_key": run.get("generation_key"),
        "decision_date": run.get("decision_date"),
        "item_count": len(items),
        "diagnostics": list(run.get("diagnostics") or [])[:100],
    }


def _watermark_date(watermark: dict[str, object]) -> date:
    value = watermark.get("verified_completed_through")
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise RuntimeError("Completed daily-bar watermark has an invalid date.") from exc
    raise RuntimeError("Completed daily-bar watermark is missing its verified date.")


def _parse_uuid(value: str | UUID, *, label: str) -> UUID:
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {label}.") from exc


def _skipped_phase(code: str) -> dict[str, object]:
    return {"status": "skipped", "code": code}


def _failed_phase(code: str, exc: Exception) -> dict[str, object]:
    return {
        "status": "failed",
        "code": code,
        "error_type": type(exc).__name__[:128],
    }


def _execution_error(
    phase: str,
    exc: Exception,
    partial_result: dict[str, object],
) -> DailyResearchLoopExecutionError:
    return DailyResearchLoopExecutionError(
        phase,
        error_type=type(exc).__name__,
        partial_result=partial_result,
    )


def _bounded_detail_value(value: object, *, depth: int = 0) -> object:
    if depth >= 5:
        return "DETAIL_DEPTH_LIMIT"
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return value[:MAX_DETAIL_STRING_LENGTH]
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, dict):
        items = list(value.items())
        bounded = {
            str(key)[:MAX_DETAIL_STRING_LENGTH]: _bounded_detail_value(
                item,
                depth=depth + 1,
            )
            for key, item in items[:MAX_DETAIL_KEYS]
        }
        if len(items) > MAX_DETAIL_KEYS:
            bounded["_omitted_key_count"] = len(items) - MAX_DETAIL_KEYS
        return bounded
    if isinstance(value, list | tuple | set):
        items = sorted(value, key=str) if isinstance(value, set) else list(value)
        return {
            "count": len(items),
            "sample": [
                _bounded_detail_value(item, depth=depth + 1)
                for item in items[:MAX_DETAIL_ITEMS]
            ],
        }
    return type(value).__name__


def _base_result(
    *,
    status: str,
    watermark: dict[str, object],
    outcomes: dict[str, object],
    publication: dict[str, object],
) -> dict[str, object]:
    return {
        "status": status,
        "watermark": watermark,
        "outcomes": outcomes,
        "publication": publication,
        "research_signal_only": True,
        "safety": dict(SAFETY_PAYLOAD),
    }


def _report_progress(
    progress: DailyResearchProgressCallback | None,
    phase: str,
    current: int,
    total: int,
    message: str,
) -> None:
    if progress is not None:
        progress(phase, current, total, message)
