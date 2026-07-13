from __future__ import annotations

import re
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from packages.domain.models import (
    OfficialDisclosure,
    OfficialDisclosureDocument,
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


WATCHLIST_DISCLOSURE_TASK_NAME = "ingestion.ingest_watchlist_official_disclosures"
DEFAULT_LOOKBACK_DAYS = 30
MAX_LOOKBACK_DAYS = 365
DEFAULT_MAX_DOCUMENTS = 20
MAX_DOCUMENTS = 50
DEFAULT_STATUS_LIMIT = 50
MAX_STATUS_LIMIT = 200
A_SHARE_SYMBOL_PATTERN = re.compile(r"^\d{6}$")


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
) -> dict[str, object]:
    _validate_batch_limits(lookback_days, max_documents)
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
        },
        session=session,
    )


def ingest_watchlist_official_disclosures(
    *,
    session: Session,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    max_documents: int = DEFAULT_MAX_DOCUMENTS,
    request_delay_seconds: float = 1.0,
    metadata_refresher: Callable[..., dict[str, object]] = refresh_official_disclosures,
    document_ingester: Callable[..., dict[str, object]] = ingest_official_disclosure_document,
    progress_callback: Callable[[str, int, int, str], None] | None = None,
    sleep_func: Callable[[float], None] = time.sleep,
    today: date | None = None,
) -> dict[str, object]:
    _validate_batch_limits(lookback_days, max_documents)
    symbols = _eligible_watchlist_symbols(session)
    end_date = today or datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=lookback_days)
    diagnostics: list[dict[str, object]] = []
    metadata_items: list[dict[str, object]] = []
    external_call_count = 0

    total_progress = len(symbols) + max_documents
    _report(progress_callback, "metadata", 0, total_progress, "Preparing watchlist disclosure refresh.")
    for index, symbol in enumerate(symbols, start=1):
        external_call_count = _delay_between_calls(
            external_call_count,
            request_delay_seconds,
            sleep_func,
        )
        try:
            result = metadata_refresher(
                OfficialDisclosureRefreshInput(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                ),
                session=session,
            )
            counts = result.get("counts") if isinstance(result, dict) else None
            metadata_items.append(
                {
                    "symbol": symbol,
                    "status": str(result.get("status", "ok")),
                    "counts": counts if isinstance(counts, dict) else {},
                }
            )
        except (CninfoDisclosureProviderError, OfficialDisclosurePersistenceError, ValueError) as error:
            session.rollback()
            diagnostic = _safe_operation_diagnostic("metadata", symbol, error)
            diagnostics.append(diagnostic)
            metadata_items.append({"symbol": symbol, "status": "failed", "diagnostic": diagnostic})
        _report(
            progress_callback,
            "metadata",
            index,
            total_progress,
            f"Refreshed disclosure metadata for {index} of {len(symbols)} watchlist symbols.",
        )

    candidates = _pending_document_candidates(
        session=session,
        symbols=symbols,
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
            "metadata_attempt_count": len(metadata_items),
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
