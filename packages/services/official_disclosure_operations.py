from __future__ import annotations

import re
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from packages.domain.models import (
    OfficialDisclosure,
    OfficialDisclosureDocument,
    OfficialDisclosureMonitorState,
    OfficialDisclosureSection,
    TaskRun,
)
from packages.providers.cninfo_disclosure_provider import CninfoDisclosureProviderError
from packages.providers.cninfo_document_provider import CninfoDocumentProviderError
from packages.services.official_disclosure_documents import (
    OfficialDisclosureDocumentPersistenceError,
    OfficialDisclosureDocumentStorageError,
    ingest_official_disclosure_document,
    serialize_official_disclosure_document,
)
from packages.services.official_disclosures import (
    OfficialDisclosurePersistenceError,
    OfficialDisclosureRefreshInput,
    refresh_official_disclosures,
    serialize_official_disclosure,
)
from packages.services.task_runs import enqueue_task_run, expire_stale_task_runs, get_task_run_payload
from packages.services.watchlists import get_active_watchlist_scope
from packages.shared.config import settings


WATCHLIST_DISCLOSURE_TASK_NAME = "ingestion.ingest_watchlist_official_disclosures"
WATCHLIST_DISCLOSURE_SCHEDULE_TASK_NAME = "ingestion.schedule_watchlist_official_disclosures"
DEFAULT_LOOKBACK_DAYS = 30
MAX_LOOKBACK_DAYS = 365
DEFAULT_MAX_DOCUMENTS = 20
MAX_DOCUMENTS = 50
DEFAULT_STATUS_LIMIT = 50
MAX_STATUS_LIMIT = 200
A_SHARE_SYMBOL_PATTERN = re.compile(r"^\d{6}$")
IngestionMode = Literal["batch", "incremental"]


def list_watchlist_official_disclosure_evidence(
    *,
    session: Session,
    limit: int = DEFAULT_STATUS_LIMIT,
) -> dict[str, object]:
    symbols = _eligible_watchlist_symbols(session)
    bounded_limit = max(1, min(limit, MAX_STATUS_LIMIT))
    if not symbols:
        return _coverage_payload(symbols=[], disclosures=[], returned=[], session=session)

    disclosures = (
        session.query(OfficialDisclosure)
        .filter(OfficialDisclosure.symbol.in_(symbols))
        .order_by(
            OfficialDisclosure.published_at.desc(),
            OfficialDisclosure.symbol.asc(),
            OfficialDisclosure.source_document_id.asc(),
        )
        .all()
    )
    return _coverage_payload(
        symbols=symbols,
        disclosures=disclosures,
        returned=disclosures[:bounded_limit],
        session=session,
    )


def enqueue_watchlist_official_disclosure_ingestion(
    *,
    session: Session,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    max_documents: int = DEFAULT_MAX_DOCUMENTS,
    mode: IngestionMode = "batch",
) -> dict[str, object]:
    _validate_batch_limits(lookback_days, max_documents)
    _validate_mode(mode)
    expire_stale_task_runs(session)
    active = (
        session.query(TaskRun)
        .filter(
            TaskRun.task_name == WATCHLIST_DISCLOSURE_TASK_NAME,
            TaskRun.status == "running",
        )
        .order_by(TaskRun.started_at.desc())
        .first()
    )
    if active is not None:
        payload = get_task_run_payload(session, str(active.id))
        return {
            "source": "database",
            "status": "already_running",
            "task_run": payload["item"] if payload else {"id": str(active.id)},
        }
    return enqueue_task_run(
        WATCHLIST_DISCLOSURE_TASK_NAME,
        {
            "lookback_days": lookback_days,
            "max_documents": max_documents,
            "mode": mode,
        },
        session=session,
    )


def ingest_watchlist_official_disclosures(
    *,
    session: Session,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    max_documents: int = DEFAULT_MAX_DOCUMENTS,
    mode: IngestionMode = "batch",
    overlap_days: int = 3,
    retry_base_minutes: int = 60,
    retry_max_minutes: int = 1440,
    task_run_id: str | None = None,
    request_delay_seconds: float = 1.0,
    metadata_refresher: Callable[..., dict[str, object]] = refresh_official_disclosures,
    document_ingester: Callable[..., dict[str, object]] = ingest_official_disclosure_document,
    progress_callback: Callable[[str, int, int, str], None] | None = None,
    sleep_func: Callable[[float], None] = time.sleep,
    today: date | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    _validate_batch_limits(lookback_days, max_documents)
    _validate_monitor_limits(overlap_days, retry_base_minutes, retry_max_minutes)
    _validate_mode(mode)
    symbols = _eligible_watchlist_symbols(session)
    operation_now = _as_utc(now) or datetime.now(timezone.utc)
    end_date = today or operation_now.date()
    start_date = end_date - timedelta(days=lookback_days)
    diagnostics: list[dict[str, object]] = []
    metadata_items: list[dict[str, object]] = []
    external_call_count = 0

    total_progress = len(symbols) + max_documents
    _report(progress_callback, "metadata", 0, total_progress, "Preparing watchlist disclosure refresh.")
    successful_symbols: list[str] = []
    backoff_symbols: list[str] = []
    for index, symbol in enumerate(symbols, start=1):
        state = _get_or_create_monitor_state(symbol, session=session)
        if mode == "incremental" and _is_in_backoff(state, operation_now):
            backoff_symbols.append(symbol)
            metadata_items.append(
                {
                    "symbol": symbol,
                    "status": "backoff",
                    "next_retry_at": _isoformat(state.next_retry_at),
                }
            )
            _report(
                progress_callback,
                "metadata",
                index,
                total_progress,
                f"Skipped {index} of {len(symbols)} watchlist symbols during retry backoff.",
            )
            continue
        symbol_start_date = _incremental_start_date(
            state,
            start_date=start_date,
            overlap_days=overlap_days,
            mode=mode,
        )
        state.last_attempted_at = operation_now
        state.status = "running"
        state.last_task_run_id = _parse_task_run_id(task_run_id)
        session.commit()
        external_call_count = _delay_between_calls(
            external_call_count,
            request_delay_seconds,
            sleep_func,
        )
        try:
            result = metadata_refresher(
                OfficialDisclosureRefreshInput(
                    symbol=symbol,
                    start_date=symbol_start_date,
                    end_date=end_date,
                ),
                session=session,
            )
            counts = result.get("counts") if isinstance(result, dict) else None
            created_count = _count_value(counts, "created")
            _record_monitor_success(
                state,
                symbol=symbol,
                created_count=created_count,
                now=operation_now,
                task_run_id=task_run_id,
                session=session,
            )
            successful_symbols.append(symbol)
            metadata_items.append(
                {
                    "symbol": symbol,
                    "status": str(result.get("status", "ok")),
                    "counts": counts if isinstance(counts, dict) else {},
                    "date_range": {
                        "start": symbol_start_date.isoformat(),
                        "end": end_date.isoformat(),
                    },
                }
            )
        except (CninfoDisclosureProviderError, OfficialDisclosurePersistenceError, ValueError) as error:
            session.rollback()
            diagnostic = _safe_operation_diagnostic("metadata", symbol, error)
            _record_monitor_failure(
                symbol=symbol,
                diagnostic=diagnostic,
                now=operation_now,
                retry_base_minutes=retry_base_minutes,
                retry_max_minutes=retry_max_minutes,
                task_run_id=task_run_id,
                session=session,
            )
            diagnostics.append(diagnostic)
            metadata_items.append({"symbol": symbol, "status": "failed", "diagnostic": diagnostic})
        _report(
            progress_callback,
            "metadata",
            index,
            total_progress,
            f"Refreshed disclosure metadata for {index} of {len(symbols)} watchlist symbols.",
        )

    document_symbols = successful_symbols if mode == "incremental" else symbols
    candidates = _pending_document_candidates(
        session=session,
        symbols=document_symbols,
        start_date=start_date,
        end_date=end_date,
        limit=max_documents,
    )
    document_items: list[dict[str, object]] = []
    counts = {
        "created": 0,
        "unchanged": 0,
        "restored": 0,
        "non_citable": 0,
        "failed": 0,
    }
    for index, disclosure in enumerate(candidates, start=1):
        external_call_count = _delay_between_calls(
            external_call_count,
            request_delay_seconds,
            sleep_func,
        )
        try:
            result = document_ingester(str(disclosure.id), session=session)
            action = str(result.get("action", "created"))
            status = str(result.get("status", "ok"))
            if action in counts:
                counts[action] += 1
            if status != "ok":
                counts["non_citable"] += 1
            document = result.get("document")
            document_items.append(
                {
                    "disclosure_id": str(disclosure.id),
                    "symbol": disclosure.symbol,
                    "title": disclosure.title,
                    "status": status,
                    "action": action,
                    "document": document if isinstance(document, dict) else None,
                }
            )
        except (
            CninfoDocumentProviderError,
            OfficialDisclosureDocumentPersistenceError,
            OfficialDisclosureDocumentStorageError,
            ValueError,
        ) as error:
            session.rollback()
            counts["failed"] += 1
            diagnostic = _safe_operation_diagnostic("document", disclosure.symbol, error)
            diagnostics.append(diagnostic)
            document_items.append(
                {
                    "disclosure_id": str(disclosure.id),
                    "symbol": disclosure.symbol,
                    "title": disclosure.title,
                    "status": "failed",
                    "diagnostic": diagnostic,
                }
            )
        _report(
            progress_callback,
            "documents",
            len(symbols) + index,
            total_progress,
            f"Processed {index} of {len(candidates)} disclosure documents.",
        )

    if not symbols or (not candidates and not diagnostics):
        status = "no_data"
    elif counts["failed"] or any(item["status"] == "failed" for item in metadata_items):
        status = "partial" if document_items or any(item["status"] != "failed" for item in metadata_items) else "failed"
    else:
        status = "ok"
    return {
        "status": status,
        "scope": "watchlist",
        "date_range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "symbols": symbols,
        "summary": {
            "eligible_symbol_count": len(symbols),
            "metadata_attempt_count": len(metadata_items) - len(backoff_symbols),
            "metadata_success_count": len(successful_symbols),
            "backoff_skipped_count": len(backoff_symbols),
            "new_disclosure_count": sum(
                _count_value(item.get("counts"), "created") for item in metadata_items
            ),
            "candidate_document_count": len(candidates),
            "processed_document_count": len(document_items),
            **counts,
        },
        "metadata_items": metadata_items,
        "items": document_items,
        "diagnostics": diagnostics[:100],
        "safety": {
            "watchlist_only": True,
            "sequential_requests": True,
            "mode": mode,
            "overlap_days": overlap_days if mode == "incremental" else 0,
            "max_documents": max_documents,
            "request_delay_seconds": max(0.0, request_delay_seconds),
            "no_automated_trading": True,
        },
    }


def _eligible_watchlist_symbols(session: Session) -> list[str]:
    return sorted(
        {
            symbol.strip()
            for item in get_active_watchlist_scope(session)
            if str(item["market"]).strip().upper() == "CN"
            and A_SHARE_SYMBOL_PATTERN.fullmatch(symbol := str(item["symbol"]).strip())
        }
    )


def _pending_document_candidates(
    *, session: Session, symbols: list[str], start_date: date, end_date: date, limit: int
) -> list[OfficialDisclosure]:
    if not symbols:
        return []
    start_at = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end_at = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    rows = (
        session.query(OfficialDisclosure)
        .filter(
            OfficialDisclosure.symbol.in_(symbols),
            OfficialDisclosure.published_at >= start_at,
            OfficialDisclosure.published_at < end_at,
        )
        .order_by(
            OfficialDisclosure.published_at.desc(),
            OfficialDisclosure.symbol.asc(),
            OfficialDisclosure.source_document_id.asc(),
        )
        .all()
    )
    pending: list[OfficialDisclosure] = []
    for disclosure in rows:
        latest = _latest_document(disclosure.id, session=session)
        if latest is None or latest.extraction_status != "extracted":
            pending.append(disclosure)
        if len(pending) >= limit:
            break
    return pending


def _coverage_payload(
    *, symbols: list[str], disclosures: list[OfficialDisclosure], returned: list[OfficialDisclosure], session: Session
) -> dict[str, object]:
    all_states = [_coverage_state(disclosure, session=session) for disclosure in disclosures]
    returned_ids = {disclosure.id for disclosure in returned}
    items = [state for disclosure, state in zip(disclosures, all_states, strict=True) if disclosure.id in returned_ids]
    return {
        "status": "ok" if symbols else "no_data",
        "scope": "watchlist",
        "symbols": symbols,
        "summary": {
            "eligible_symbol_count": len(symbols),
            "metadata_disclosure_count": len(disclosures),
            "with_document_count": sum(item["document"] is not None for item in all_states),
            "extracted_document_count": sum(item["status"] == "extracted" for item in all_states),
            "metadata_only_count": sum(item["status"] == "metadata_only" for item in all_states),
            "non_citable_count": sum(item["status"] in {"no_text", "failed", "rejected"} for item in all_states),
            "citable_section_count": sum(
                value if isinstance((value := item.get("section_count")), int) else 0
                for item in all_states
            ),
            "returned": len(items),
        },
        "monitoring": _monitoring_payload(symbols, session=session),
        "items": items,
        "diagnostics": [],
        "evidence_boundary": {
            "metadata_citation_prefix": "official_disclosure:",
            "content_citation_prefix": "official_disclosure_section:",
            "content_requires_extracted_sections": True,
        },
    }


def _coverage_state(disclosure: OfficialDisclosure, *, session: Session) -> dict[str, object]:
    latest = _latest_document(disclosure.id, session=session)
    section_count = 0
    if latest is not None and latest.extraction_status == "extracted":
        section_count = (
            session.query(OfficialDisclosureSection)
            .filter(OfficialDisclosureSection.document_id == latest.id)
            .count()
        )
    payload = serialize_official_disclosure(disclosure)
    return {
        **payload,
        "status": latest.extraction_status if latest is not None else "metadata_only",
        "document": serialize_official_disclosure_document(latest) if latest is not None else None,
        "section_count": section_count,
        "content_citable": latest is not None and latest.extraction_status == "extracted" and section_count > 0,
    }


def _latest_document(disclosure_id, *, session: Session) -> OfficialDisclosureDocument | None:
    return (
        session.query(OfficialDisclosureDocument)
        .filter(OfficialDisclosureDocument.official_disclosure_id == disclosure_id)
        .order_by(
            OfficialDisclosureDocument.retrieved_at.desc(),
            OfficialDisclosureDocument.created_at.desc(),
        )
        .first()
    )


def _validate_batch_limits(lookback_days: int, max_documents: int) -> None:
    if not 1 <= lookback_days <= MAX_LOOKBACK_DAYS:
        raise ValueError(f"lookback_days must be between 1 and {MAX_LOOKBACK_DAYS}.")
    if not 1 <= max_documents <= MAX_DOCUMENTS:
        raise ValueError(f"max_documents must be between 1 and {MAX_DOCUMENTS}.")


def _validate_mode(mode: str) -> None:
    if mode not in {"batch", "incremental"}:
        raise ValueError("mode must be batch or incremental.")


def _validate_monitor_limits(
    overlap_days: int,
    retry_base_minutes: int,
    retry_max_minutes: int,
) -> None:
    if not 0 <= overlap_days <= 30:
        raise ValueError("overlap_days must be between 0 and 30.")
    if retry_base_minutes < 1:
        raise ValueError("retry_base_minutes must be at least 1.")
    if retry_max_minutes < retry_base_minutes:
        raise ValueError("retry_max_minutes must be greater than or equal to retry_base_minutes.")


def _get_or_create_monitor_state(
    symbol: str,
    *,
    session: Session,
) -> OfficialDisclosureMonitorState:
    state = (
        session.query(OfficialDisclosureMonitorState)
        .filter(
            OfficialDisclosureMonitorState.source == "cninfo",
            OfficialDisclosureMonitorState.symbol == symbol,
        )
        .first()
    )
    if state is None:
        state = OfficialDisclosureMonitorState(source="cninfo", symbol=symbol)
        session.add(state)
        session.flush()
    return state


def _incremental_start_date(
    state: OfficialDisclosureMonitorState,
    *,
    start_date: date,
    overlap_days: int,
    mode: IngestionMode,
) -> date:
    if mode != "incremental" or state.cursor_published_at is None:
        return start_date
    cursor_at = _as_utc(state.cursor_published_at)
    if cursor_at is None:
        return start_date
    cursor_date = cursor_at.date()
    return max(start_date, cursor_date - timedelta(days=overlap_days))


def _record_monitor_success(
    state: OfficialDisclosureMonitorState,
    *,
    symbol: str,
    created_count: int,
    now: datetime,
    task_run_id: str | None,
    session: Session,
) -> None:
    latest = (
        session.query(OfficialDisclosure)
        .filter(
            OfficialDisclosure.source == "cninfo",
            OfficialDisclosure.symbol == symbol,
        )
        .order_by(
            OfficialDisclosure.published_at.desc(),
            OfficialDisclosure.source_document_id.desc(),
        )
        .first()
    )
    state.last_attempted_at = now
    state.last_success_at = now
    state.status = "succeeded"
    state.consecutive_failures = 0
    state.next_retry_at = None
    state.last_error_code = None
    state.last_error_message = None
    state.last_new_disclosure_count = created_count
    state.last_task_run_id = _parse_task_run_id(task_run_id)
    if latest is not None:
        state.cursor_published_at = latest.published_at
        state.cursor_source_document_id = latest.source_document_id
    session.commit()


def _record_monitor_failure(
    *,
    symbol: str,
    diagnostic: dict[str, object],
    now: datetime,
    retry_base_minutes: int,
    retry_max_minutes: int,
    task_run_id: str | None,
    session: Session,
) -> None:
    state = _get_or_create_monitor_state(symbol, session=session)
    failures = state.consecutive_failures + 1
    retry_minutes = min(retry_max_minutes, retry_base_minutes * (2 ** (failures - 1)))
    state.last_attempted_at = now
    state.last_failure_at = now
    state.status = "failed"
    state.consecutive_failures = failures
    state.next_retry_at = now + timedelta(minutes=retry_minutes)
    state.last_error_code = str(diagnostic["code"])
    state.last_error_message = str(diagnostic["message"])
    state.last_task_run_id = _parse_task_run_id(task_run_id)
    session.commit()


def _is_in_backoff(state: OfficialDisclosureMonitorState, now: datetime) -> bool:
    retry_at = _as_utc(state.next_retry_at)
    return retry_at is not None and retry_at > now


def _monitoring_payload(symbols: list[str], *, session: Session) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    states = {
        state.symbol: state
        for state in session.query(OfficialDisclosureMonitorState)
        .filter(
            OfficialDisclosureMonitorState.source == "cninfo",
            OfficialDisclosureMonitorState.symbol.in_(symbols),
        )
        .all()
    } if symbols else {}
    items = [
        _serialize_monitor_state(symbol, states.get(symbol), now=now)
        for symbol in symbols
    ]
    freshness_counts = {
        freshness: sum(item["freshness"] == freshness for item in items)
        for freshness in ("fresh", "stale", "backoff", "never")
    }
    return {
        "enabled": settings.disclosure_monitor_enabled,
        "interval_minutes": max(15, settings.disclosure_monitor_interval_minutes),
        "freshness_sla_hours": max(1, settings.disclosure_monitor_freshness_hours),
        "overlap_days": max(0, settings.disclosure_monitor_overlap_days),
        "summary": {
            "tracked_symbol_count": len(states),
            "fresh_symbol_count": freshness_counts["fresh"],
            "stale_symbol_count": freshness_counts["stale"],
            "backoff_symbol_count": freshness_counts["backoff"],
            "never_succeeded_symbol_count": freshness_counts["never"],
            "new_disclosure_count": sum(
                _count_value(item, "last_new_disclosure_count") for item in items
            ),
        },
        "items": items,
        "research_boundary": {
            "new_disclosures_require_human_review": True,
            "automatic_investment_conclusions": False,
        },
    }


def _serialize_monitor_state(
    symbol: str,
    state: OfficialDisclosureMonitorState | None,
    *,
    now: datetime,
) -> dict[str, object]:
    if state is None:
        return {
            "symbol": symbol,
            "source": "cninfo",
            "freshness": "never",
            "status": "never",
            "cursor_published_at": None,
            "cursor_source_document_id": None,
            "last_attempted_at": None,
            "last_success_at": None,
            "last_failure_at": None,
            "next_retry_at": None,
            "consecutive_failures": 0,
            "last_new_disclosure_count": 0,
            "diagnostic": None,
        }
    success_at = _as_utc(state.last_success_at)
    if _is_in_backoff(state, now):
        freshness = "backoff"
    elif success_at is None:
        freshness = "never"
    elif success_at < now - timedelta(hours=max(1, settings.disclosure_monitor_freshness_hours)):
        freshness = "stale"
    else:
        freshness = "fresh"
    diagnostic = None
    if state.last_error_code or state.last_error_message:
        diagnostic = {
            "source": state.source,
            "code": state.last_error_code,
            "message": state.last_error_message,
        }
    return {
        "symbol": symbol,
        "source": state.source,
        "freshness": freshness,
        "status": state.status,
        "cursor_published_at": _isoformat(state.cursor_published_at),
        "cursor_source_document_id": state.cursor_source_document_id,
        "last_attempted_at": _isoformat(state.last_attempted_at),
        "last_success_at": _isoformat(state.last_success_at),
        "last_failure_at": _isoformat(state.last_failure_at),
        "next_retry_at": _isoformat(state.next_retry_at),
        "consecutive_failures": state.consecutive_failures,
        "last_new_disclosure_count": state.last_new_disclosure_count,
        "diagnostic": diagnostic,
    }


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _isoformat(value: datetime | None) -> str | None:
    normalized = _as_utc(value)
    return normalized.isoformat() if normalized is not None else None


def _parse_task_run_id(task_run_id: str | None) -> UUID | None:
    return UUID(task_run_id) if task_run_id else None


def _count_value(value: object, key: str) -> int:
    if not isinstance(value, dict):
        return 0
    count = value.get(key)
    return count if isinstance(count, int) and not isinstance(count, bool) else 0


def _delay_between_calls(
    call_count: int, delay_seconds: float, sleep_func: Callable[[float], None]
) -> int:
    if call_count > 0 and delay_seconds > 0:
        sleep_func(delay_seconds)
    return call_count + 1


def _safe_operation_diagnostic(stage: str, symbol: str, error: Exception) -> dict[str, object]:
    code = getattr(error, "code", None)
    message = getattr(error, "message", None)
    return {
        "source": "cninfo",
        "stage": stage,
        "symbol": symbol,
        "status": "failed",
        "severity": "warning",
        "code": str(code or f"DISCLOSURE_{stage.upper()}_FAILED"),
        "message": str(message or f"Official disclosure {stage} operation failed."),
    }


def _report(
    callback: Callable[[str, int, int, str], None] | None,
    phase: str,
    current: int,
    total: int,
    message: str,
) -> None:
    if callback is not None:
        callback(phase, current, total, message)
